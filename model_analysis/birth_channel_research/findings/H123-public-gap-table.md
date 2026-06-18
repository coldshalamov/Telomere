# H123 - Public Gap Table

## Question

Can a frozen public table choose the witness gap `G(context)` so the decoder can
derive `W = T_pub - G(context)` without a per-record gap selector?

This keeps the H121/H122 optimistic typed-board assumption: `T_pub` is still
treated as known for the interval. The table is public, trained on independent
local-oracle covers, and then held fixed for evaluation.

## Result

The table improves the lower bound but does not produce a codec row.

Focused held-out repeats at `atoms=128`, `passes=4`, `q=0.10`,
`min_rewrite=0.25`:

```text
public_lane_raw, exact_arity:
  -0.006460 bits/atom/pass, fail 0.593750

public_lane_raw, lane_exact_arity:
  -0.010851 bits/atom/pass, fail 0.437500

H114_raw_lower, exact_arity:
  -0.002604 bits/atom/pass, fail 0.531250

H114_raw_lower, lane_exact_arity:
  +0.001085 bits/atom/pass, fail 0.437500
```

## Interpretation

The public table can make finite successful trials look negative, but a large
fraction of held-out trials cannot satisfy forced due-refresh. Treating those
failures as absent is an unpaid stale-record exception channel. H124 prices
fallback repair for those rows.

## Artifact

`model_analysis/birth_channel_research/H123-public_gap_table.py`
