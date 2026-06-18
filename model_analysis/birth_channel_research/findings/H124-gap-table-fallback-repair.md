# H124 - Gap Table Fallback Repair

## Question

If H123 fails because due records cannot always refresh, can failed due records
expire to raw material cheaply enough to preserve the apparent crossing?

Modes:

- `force_refresh`: due age-1 records must be covered by new records.
- `expire_raw_lower_bound`: due records become markerless raw bits with their
  grouping preserved.
- `expire_raw_atoms`: due records become fixed `B`-bit markerless raw atoms.
- `expire_literal_items`: due records become literal-marked block items.

## Result

Raw fallback can make the lower-bound row negative, but the missing raw/record
type placement channel is much larger than the margin.

Focused held-out repeat:

```text
public_lane_raw, exact_arity, expire_raw_atoms:
  delta/atom/pass        -0.014587
  type bitmap/atom/pass  +0.157235
  type runs/atom/pass    +0.261375

public_lane_raw, lane_exact_arity, expire_raw_atoms:
  delta/atom/pass        -0.023438
  type bitmap/atom/pass  +0.193945
  type runs/atom/pass    +0.303097
```

Literal fallback destroys the margin:

```text
public_lane_raw, exact_arity, expire_literal_items:
  +0.115234 bits/atom/pass

public_lane_raw, lane_exact_arity, expire_literal_items:
  +0.074870 bits/atom/pass
```

## Interpretation

The raw-atom row is a useful lower bound, not a codec. It hides an adaptive
type stream: which output items are markerless raw atoms and which are records.
The cheapest measured type bills are at least an order of magnitude larger than
the raw fallback margin.

## Artifact

`model_analysis/birth_channel_research/H124-gap_table_fallback_repair.py`
