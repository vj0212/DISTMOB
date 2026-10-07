# Optional external-trace validation

## Why this is separate

The core DISTMOB benchmark is intentionally synthetic and frozen so that every controller receives the same exogenous state and the study retains clean counterfactual semantics. Real public Wi-Fi traces do not expose all of the simulator state needed to evaluate every controller fairly (for example, a synchronized per-AP disturbance process), so external data are kept as a **validation extension**, not substituted into the primary benchmark.

## Recommended source: X-Fi dataset

X-Fi publishes real-world Wi-Fi association-attempt details from vehicle-to-infrastructure experiments across Paris, Bologna, Macao and Los Angeles. The public description includes GPS, association information, signal measurements, association timing and TCP performance fields.

Source repository: https://github.com/yangfurong/X-Fi_dataset
Paper: Yang et al., *Revisiting WiFi offloading in the wild for V2I applications*, Computer Networks, 2022.

## What DISTMOB can validate from it

The optional external analysis should check: (1) empirical speed distributions, (2) association/dwell-time distributions, (3) RSSI/signal variability, (4) handover/reassociation frequency, and (5) relationship between signal conditions and achieved goodput. These checks strengthen the realism discussion without pretending that the external trace can be used as a complete counterfactual replay.

## Data handling

The raw external dataset is intentionally **not copied into this repository**. Obtain it from the authors' public source and follow its citation and usage terms.
