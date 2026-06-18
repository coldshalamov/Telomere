# H125 - Public Raw Lane Repair

## Question

Can the H124 markerless raw fallback be made stateless by putting raw atoms in
public output lanes and records in the remaining lanes?

This tests both isolated raw slots and contiguous raw bands inside a fixed
public period. The H123 lane context is synced to the same public period.

## Result

The tested fixed-clock lanes fail the required cover.

At `atoms=128`, `passes=4`, `min_rewrite=0.25`, `public_lane_raw`, all tested
rows had `fail=1.0`:

```text
period 4, raw_run 1..3, phase 0
period 8, raw_run 1..3, phase 0
period 4, raw_run 3, phases 1..3
period 8, raw_run 7, phase 0
```

## Interpretation

Fixed raw lanes are parseable, but they are too rigid. The optimal H124 type
stream is sparse and adaptive; a public clock demands raw atoms in every raw
slot and records in every non-raw slot. That overconstrains the output geometry.

## Artifact

`model_analysis/birth_channel_research/H125-public_raw_lane_repair.py`
