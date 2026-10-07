# DISTMOB

## Disturbance-Aware Mobility Control for Mobile Networks

**DISTMOB** is a research-engineering simulation project studying a practical network-control problem:

> **When users move through a wireless network, how should the system decide which Access Point (AP) each user should be associated with when signal quality, congestion, mobility, and disturbances keep changing?**

In everyday life, this is similar to what happens when:

- you walk through a building and your phone moves between Wi-Fi APs;
- one AP becomes crowded while another has spare capacity;
- the signal from your current AP gradually deteriorates;
- temporary disturbances affect network quality;
- switching too aggressively causes unnecessary handovers;
- the best decision depends not only on **what is best now**, but also on **what is likely to happen next**.

DISTMOB models this as a **dynamic AP-association and control problem** and compares classical handover rules, load-aware association, predictive disturbance-aware control, robustness and safety extensions, a constrained global assignment planner, a supervisory controller, and a lightweight tabular reinforcement-learning baseline.

---

# At a Glance

| | Result |
|---|---:|
| **Controllers evaluated** | 11 |
| **Paired robustness seeds** | 10 |
| **Stress combinations** | 6 |
| **Primary comparison** | Stable-global vs Load-aware |
| **Outage** | 0.2602 → **0.1692** |
| **Jain fairness** | 0.7757 → **0.8674** |
| **Latency proxy** | 1.8111 → **1.3416** |
| **Handover rate** | 0.2420 → **0.00142** |
| **P05 throughput** | 3.4521 → **3.0335 Mbps** |
| **P05 throughput trade-off** | **−12.1%** |
| **Mean handovers, switch penalty ON** | **4.4** |
| **Mean handovers, switch penalty OFF** | **109.9** |
| **Served-demand improvement** | Positive, but **not statistically significant after Holm correction** |

**Important:** These are results under the stated synthetic simulation model. They are not claims of universal network superiority or field validation.

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

As the user moves:

- AP 1's signal may weaken.
- AP 2 may become stronger.
- AP 1 may become congested.
- A temporary disturbance may affect either AP.
- Switching too aggressively may cause unnecessary handovers.

So the system repeatedly faces a decision:

> **Should the user remain associated with the current AP, or switch to another AP?**

With many users, this becomes a network-level problem because assigning one user to an AP changes that AP's load and can therefore affect other users.

DISTMOB therefore treats **AP association as a dynamic control problem**, rather than simply selecting the strongest signal.

### AP association vs handover

These terms are related but not identical:

- **AP association:** which AP a user is assigned/connected to at a particular time.
- **Handover:** a change in that association from one AP to another.

For example:

```text
t1     User 1 → AP1
t2     User 1 → AP1
t3     User 1 → AP1
t4     User 1 → AP2   ← handover
t5     User 1 → AP2
```

DISTMOB therefore studies both **which AP should serve each user** and **how often those assignments should change**.

---

# 2. Why Go Beyond "Connect to the Strongest AP"?

A natural starting point is:

> **"Just connect each user to the AP with the strongest signal."**

That works as a useful baseline, but it ignores several interactions.

### Problem 1 — Signal is not the whole story

A strong AP can already be heavily loaded.

```text
AP1: ████████████████████  95% loaded
AP2: ███████               35% loaded
```

Sending another user to AP1 simply because its signal is stronger may hurt the network overall.

### Problem 2 — Users are moving

The AP that is best **right now** may not remain best a few seconds later.

### Problem 3 — Disturbances change the environment

A temporary disturbance can change link quality even when the user's physical position has barely changed.

### Problem 4 — Users interact through shared AP capacity

The association decision for User A can affect User B because both may compete for the same AP resources.

### Problem 5 — Switching has a cost

Always chasing the currently best AP can produce excessive handovers.

Therefore, DISTMOB progressively asks:

```text
Can we make a better local decision?
        ↓
Can we account for congestion?
        ↓
Can we account for future conditions?
        ↓
Can we account for uncertainty and risk?
        ↓
Can we coordinate users globally?
        ↓
Can we explicitly control the cost of switching?
```

This is the motivation for moving from simple local policies toward **Stable-global**.

---

# 3. Where We Started → Where We Reached

The project evolved through multiple iterations rather than beginning with the final controller.

## Starting point

The original research question was:

> **Can disturbance-aware control make better AP-association decisions than conventional handover rules?**

The first versions focused on local, user-level strategies:

- RSSI-based association
- Hysteresis
- Time-to-trigger (TTT)
- Load-aware association
- Disturbance-aware predictive control

During development, several assumptions were challenged.

For example:

- an early predictive implementation did not correctly propagate future user mobility;
- the planner's internal rate model differed from the authoritative evaluation model;
- average throughput alone did not adequately reveal the QoS/stability trade-off.

Rather than hiding these problems, the project converted them into explicit experiments and design changes.

## Where we reached

The final system contains:

- **10 paired random seeds** for robustness analysis;
- **6 disturbance/mobility stress combinations**;
- prediction-horizon sensitivity experiments;
- planner/evaluator model-mismatch experiments;
- an explicit oracle-planner control condition;
- zero-switch-penalty ablation;
- tail-QoS analysis;
- paired statistical testing;
- runtime benchmarking;
- trace-driven replay;
- an optional external-trace validation path;
- reproducible experiment and report-generation scripts;
- automated tests and final-release validation.

The project ultimately became less about proving:

> **"One controller always wins."**

and more about answering:

> **"Why does a policy behave the way it does, where does it fail, what assumptions does it depend on, and what trade-offs does it introduce?"**

---

# 4. The Controllers

DISTMOB compares progressively more sophisticated association strategies.

| Controller | Core idea | Everyday interpretation |
|---|---|---|
| **RSSI** | Highest current signal/link score | "Use whichever AP looks strongest now." |
| **Hysteresis** | Switch only after a sufficient advantage | "Don't switch for a tiny improvement." |
| **TTT** | Candidate must remain better for a period | "Wait and make sure the improvement is real." |
| **Load-aware** | Penalize congested APs | "Don't send everyone to the crowded AP." |
| **DARC-no-observer** | Direct disturbance input | "Use the disturbance we see now." |
| **DARC** | Disturbance observer + finite-horizon prediction | "Estimate what may happen next." |
| **Robust-DARC** | Adds mobility/uncertainty penalties | "Be more cautious when conditions are uncertain." |
| **Shield-DARC** | Risk-triggered conservative mode | "When things look dangerous, switch to a safer policy." |
| **Regime orchestrator** | Supervisory switching among modes | "Change strategy depending on the network regime." |
| **Stable-global** | Joint constrained AP assignment + switch penalty | "Coordinate all users instead of optimizing each user independently." |
| **Q-learning** | Tabular RL baseline | "Learn decisions through interaction with the environment." |

The overall progression is:

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

# 5. Why Stable-global?

The purpose of Stable-global is **not** to assume that more complex optimization must be better.

It tests a specific hypothesis:

> **Because users compete for shared AP capacity, jointly optimizing user-AP assignments may produce better network-level outcomes than making each association decision independently.**

Local policies primarily reason about an individual user's current situation.

Stable-global instead considers the assignment of users across APs together while incorporating:

- AP capacity;
- demand gaps;
- switching cost;
- mobility/risk terms;
- planner-side rate estimates.

Conceptually:

```text
Local policy:

User 1 → best AP for User 1
User 2 → best AP for User 2
User 3 → best AP for User 3
             ↓
       network interaction
```

versus:

```text
Stable-global:

User 1 ─┐
User 2 ─┼──→ Joint assignment problem ──→ AP assignments
User 3 ─┘
             ↓
       network-level objective
```

This does **not** mean Stable-global is universally better. It means the project explicitly tests whether the additional global coordination is worth its complexity and what trade-offs it creates.

---

# 6. What the System Actually Optimizes

DISTMOB does not define success as simply maximizing instantaneous throughput.

It evaluates several dimensions.

## Quality of service

- Served-demand fraction
- Mean satisfaction
- P05 satisfaction
- P05 throughput
- Outage

## Network fairness

- Jain's fairness index

## Stability

- Handover rate
- Total handovers

## Responsiveness

- Latency proxy

This matters because improving one metric can hurt another.

For example:

> A controller that constantly switches users may find slightly better instantaneous links while creating excessive mobility churn.

DISTMOB therefore evaluates **QoS, fairness, responsiveness, and stability together**.

---

# 7. Primary Evidence — 10 Paired Seeds

The main robustness comparison uses **10 paired random seeds** rather than relying on a single simulation run.

## Stable-global vs Load-aware

| Metric | Load-aware | Stable-global | Change |
|---|---:|---:|---:|
| Served-demand fraction | **0.9275** | **0.9482** | +0.0207 |
| Outage | **0.2602** | **0.1692** | −35.0% |
| Jain fairness | **0.7757** | **0.8674** | +0.0917 |
| Latency proxy | **1.8111** | **1.3416** | −25.9% |
| Handover rate | **0.2420** | **0.00142** | ≈−99.4% |
| P05 throughput | **3.4521 Mbps** | **3.0335 Mbps** | **−12.1%** |

### What the numbers mean

Under the tested simulation model, Stable-global produces:

- lower outage;
- higher Jain fairness;
- lower latency proxy;
- dramatically fewer handovers;

while paying a measurable **12.1% P05-throughput cost**.

The served-demand fraction also improves:

```text
0.9275 → 0.9482
```

but this improvement is **not statistically significant after Holm correction**.

That distinction matters: the mean difference is useful evidence, but it should not be presented as statistically established superiority.

---

# 8. The Main Trade-off

The project does **not** claim that Stable-global improves every metric.

The clearest documented trade-off is:

```text
                         Load-aware   Stable-global
P05 throughput           3.4521 Mbps  3.0335 Mbps
                                      ↓
                                    −12.1%
```

In everyday terms:

> Stable-global does a better job keeping the overall network stable and fair under the tested model, but the bottom tail of users can receive less throughput.

This is exactly why P05 metrics are included.

Looking only at averages could have hidden this behavior.

---

# 9. The Most Important Ablation — Why Is Churn So Low?

Stable-global produces extremely low handover rates.

That raises an important question:

> **Is the low churn actually caused by the stability term, or is it simply an artifact of the simulated environment?**

To test this, the explicit switch penalty is removed.

## Zero-switch-penalty ablation

```text
Stable-global
     │
     │ switch penalty ON
     ▼
~4.4 mean handovers


Stable-global-no-switch
     │
     │ switch penalty OFF
     ▼
~109.9 mean handovers
```

This is approximately a **25× increase** in mean handovers.

Interestingly, removing the penalty improves some QoS metrics.

### Interpretation

The ablation provides strong evidence that the low-churn behavior is specifically associated with the **switch-regularization term** in the tested optimization setup, rather than being merely a property of the environment.

In everyday terms:

> If the system is explicitly told that unnecessary AP switching has a cost, it prefers to stay with a reasonable AP rather than constantly chase small short-term improvements.

Remove that cost, and the optimizer becomes much more willing to switch.

---

# 10. Planner vs Evaluator — What If the Model Is Wrong?

A major methodological concern is:

> **Does the global planner know exactly the same model that the evaluator uses?**

If it did, the planner could effectively receive privileged information.

DISTMOB therefore uses an intentionally imperfect fixed planner proxy for the main Stable-global condition:

```text
Planner-side model

pathloss exponent = 2.60
SNR bias          = -1.20 dB
rate scale        = 7.60

        ↓

Planner chooses assignments

        ↓

Authoritative evaluator

        ↓

Actual simulated outcome
```

The project also contains:

### `stable_global_oracle`

This control condition gives the planner an evaluator-matched model.

The release therefore distinguishes between:

- normal planner assumptions;
- oracle planner assumptions;
- planner/evaluator mismatch;
- actual evaluated performance.

This prevents the main result from quietly depending on a perfectly matched internal model.

---

# 11. Model-Mismatch Experiment

The project explicitly tests increasing disagreement between the planner's internal model and the authoritative evaluator.

The question is:

> **Does the global-assignment approach remain useful when its internal model is wrong?**

The experiment includes:

- mild mismatch;
- moderate mismatch;
- strong mismatch;

and tracks internal planner-score drift.

The purpose is **not** to prove that the planner is robust to every possible modeling error.

Instead, it tests whether the observed behavior remains defensible when the planning model is deliberately imperfect.

This is important because real engineering systems rarely operate with a perfect model of their environment.

---

# 12. Predictive Control — Correcting an Early Assumption

One of the most important development lessons was that simply calling a controller **"predictive"** does not make it predictive.

An early implementation discounted future disturbance but did not correctly propagate future user mobility.

The corrected DARC implementation explicitly propagates future user state when evaluating future decisions.

Conceptually:

```text
Current state
     │
     ▼
Predict future user movement
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

## Horizon sensitivity

In the tested configuration, increasing the prediction horizon from **1 → 12 steps** changed:

```text
Outage:

0.465  →  0.210
```

and:

```text
Served-demand fraction:

0.812  →  0.951
```

These results support the conclusion that, **under this simulation model**, additional temporal context can improve predictive-control decisions.

They should not be interpreted as proof that a longer horizon is universally better in real networks.

---

# 13. Stress Testing

A controller that performs well in one carefully chosen scenario is not enough.

DISTMOB therefore varies:

- disturbance volatility;
- maximum user speed;
- random seed.

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

The purpose is not simply:

> "Does the controller work?"

but:

> **"How does the controller behave as mobility and disturbance conditions become more difficult?"**

---

# 14. Statistical Validation

The project does not rely only on visually comparing averages.

The seed-level analysis includes:

- paired t-test;
- Wilcoxon signed-rank test;
- Cohen's \(d_z\);
- bootstrap confidence intervals;
- Holm multiple-comparison correction.

## Important statistical result

The served-demand improvement of Stable-global over Load-aware is **positive but not statistically significant after Holm correction**.

Therefore, the project does **not** claim:

> "Stable-global statistically dominates every baseline."

The narrower and defensible conclusion is:

> **Under the tested simulation model, Stable-global improves several important metrics — particularly outage, fairness, latency proxy and handover stability — while introducing a measurable P05-throughput trade-off.**

That distinction between **observed improvement** and **statistically established improvement** is intentional.

---

# 15. What Happens When the Environment Is Evaluated on the Same Trace?

The core benchmark uses controlled, frozen traces.

This allows different policies to experience the **same underlying mobility/disturbance trajectory**, making counterfactual policy comparison cleaner.

Conceptually:

```text
                  Same trace
                     │
        ┌────────────┼────────────┐
        │            │            │
       RSSI      Load-aware    Stable-global
        │            │            │
        └────────────┼────────────┘
                     │
                 Evaluation
```

The goal is to ensure that differences in results are attributable to the **policy**, rather than each policy receiving a different random environment.

---

# 16. Runtime and Computational Cost

DISTMOB also includes runtime benchmarking.

The final release uses a **frozen runtime protocol** for its runtime claims.

Historical v10 timings are explicitly treated as **non-comparable** because the timed operation and implementation/workload changed between versions.

Therefore:

> **Only final-release protocol measurements should be used when making runtime comparisons.**

This avoids presenting an apples-to-oranges runtime improvement as an algorithmic speedup.

---

# 17. External-Trace Extension

The main benchmark intentionally remains **synthetic and frozen**.

This is deliberate.

The controlled simulator provides observability and repeatability that may not be available in external datasets.

As an optional validation path, the repository documents the **X-Fi public Wi-Fi association dataset**, which contains:

- GPS traces;
- Wi-Fi association attempts;
- signal measurements;
- TCP performance fields;

across:

- Paris;
- Bologna;
- Macao;
- Los Angeles.

The external dataset is **not copied into this repository**.

Users should obtain it from the original authors and follow the dataset's citation and usage terms.

The external trace is intended to help examine whether the project's mobility/association assumptions are plausible on real-world measurements.

It is **not used as evidence for the primary controlled benchmark**, and it does not replace the synthetic experiment.

**Source:** Yang et al., *Revisiting WiFi offloading in the wild for V2I applications*, Computer Networks, 2022.

---

# 18. What I Learned From the Project

The most important outcome was not simply finding a controller with better numbers.

The project followed a repeated engineering/research cycle:

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
Fix implementation / redesign experiment
    ↓
Ablation / validation
    ↓
More defensible conclusion
```

## Lesson 1 — "Predictive" must actually predict

An early implementation did not correctly propagate future mobility.

**Lesson:** a label is not evidence of a mechanism.

---

## Lesson 2 — Complexity is not automatically an advantage

A sophisticated controller does not deserve to win simply because it contains more components.

The project deliberately retains strong classical and simpler baselines.

**Lesson:** compare against meaningful alternatives before claiming that added complexity is useful.

---

## Lesson 3 — Optimization objectives create behavior

Removing the switch penalty increased mean handovers from approximately:

```text
4.4 → 109.9
```

**Lesson:** understand what the objective function explicitly incentivizes.

---

## Lesson 4 — Average metrics can hide important failures

Average throughput alone would not have exposed the P05-throughput trade-off.

**Lesson:** inspect distributions and tail behavior, not only means.

---

## Lesson 5 — Model mismatch matters

The planner and evaluator should not silently assume perfect agreement.

**Lesson:** real engineering systems operate with imperfect models.

---

## Lesson 6 — A negative or non-significant result is still useful

The served-demand improvement was positive but did not survive Holm correction.

Instead of hiding that result, the final analysis reports it explicitly.

**Lesson:** a good experiment should be capable of disproving or weakening your preferred hypothesis.

---

# 19. Technical Architecture

```text
                         DISTMOB
                            │
              ┌─────────────┴─────────────┐
              │                           │
          Mobility                    Disturbance
           Process                      Process
              │                           │
              └─────────────┬─────────────┘
                            │
                      Network State
                            │
              ┌─────────────┴─────────────┐
              │                           │
        Local Policies              Global Planner
              │                           │
              └─────────────┬─────────────┘
                            │
                   Supervisory Control
                            │
                            ▼
                     AP Association
                            │
                            ▼
                       Evaluation
                            │
             ┌──────────────┼──────────────┐
             │              │              │
            QoS          Fairness       Stability
             │              │              │
             └──────────────┼──────────────┘
                            │
                            ▼
                  Statistical Analysis
```

---

# 20. Repository Structure

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
│
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

# 21. Reproduce the Experiments

## Install dependencies

```bash
python -m pip install -r requirements.txt
```

## Run the complete experiment suite

```bash
python scripts/run_all_experiments.py
```

## Build the report

```bash
python scripts/build_report.py
```

## Run tests

```bash
pytest -q
```

For a faster reviewer-focused refresh when the main release results already exist:

```bash
python scripts/recompute_review_fixes.py
python scripts/build_report.py
pytest -q
```

The repository is designed so that the experiment pipeline, generated results, figures, report, and validation checks can be inspected rather than relying only on the final claims.

---

# 22. Scientific Scope and Limitations

DISTMOB is a **synthetic comparative control study**.

It is **not**:

- a packet-level 4G/5G simulator;
- a complete 3GPP network simulator;
- field-validation evidence;
- a production network controller;
- a claim of universal controller superiority.

The model does not attempt to reproduce every detail of a production cellular/Wi-Fi stack, such as:

- full packet scheduling;
- detailed interference/fading;
- MCS selection;
- queue dynamics;
- real handover signaling;
- complete radio-protocol behavior.

The global planner is also centralized in the current design, which creates a scalability/deployment limitation compared with a fully distributed production architecture.

The external-trace path is documented as an extension rather than primary evidence.

Most importantly, the experiments evaluate the controllers **under the stated simulator assumptions**.

---

# 23. What the Results Do — and Do Not — Show

### The results support:

- lower outage for Stable-global under the tested model;
- higher Jain fairness;
- lower latency proxy;
- substantially lower handover rate;
- persistence of the main outage/fairness advantage under the tested planner/evaluator mismatch conditions;
- a strong relationship between the explicit switch penalty and low handover behavior.

### The results do not establish:

- universal superiority of Stable-global;
- statistically significant improvement in served-demand fraction;
- better P05 throughput;
- real-world 4G/5G performance;
- production-scale deployment readiness;
- superiority under every possible mobility, disturbance, or network configuration.

This distinction is central to the project's interpretation.

---

# 24. Final Takeaway

DISTMOB started with a relatively simple question:

> **Can disturbance-aware AP association outperform conventional handover rules?**

It evolved into a broader study:

> **How should a network make AP-association decisions when users move, APs become congested, disturbances change over time, models are imperfect, and switching itself has a cost?**

The final system combines:

- predictive control;
- robustness and safety mechanisms;
- global constrained assignment;
- supervisory regime control;
- a reinforcement-learning baseline;
- controlled simulation;
- frozen-trace comparison;
- statistical testing;
- ablation studies;
- model-mismatch analysis;
- tail-QoS evaluation;
- runtime benchmarking;
- reproducible experimentation.

The most valuable outcome is not:

> **"This algorithm always wins."**

It is:

> **"Here is a reproducible control system; here is why the design evolved; here is how its assumptions were tested; here is where it performs well; here is where it loses; and here is evidence explaining why."**

That is the engineering and research question DISTMOB is designed to investigate.
