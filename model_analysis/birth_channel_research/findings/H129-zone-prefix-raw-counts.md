# H129 - Zone Prefix Raw Counts

## Question

Can H124's adaptive raw/record type stream be approximated by fixed public
zones where each zone is parsed as:

```text
[raw atom prefix][record suffix]
```

The decoder pays one raw-count per zone instead of a per-item bitmap.

## Result

The counted-zone geometry misses badly in the tested rows.

At `atoms=128`, `passes=4`, `public_lane_raw`, `exact_arity`, `q=0.10`:

```text
min_rewrite=0.25, zone=32:
  +0.121578 bits/atom/pass
  count ledger +0.097489
  fail 0.250000

min_rewrite=0.25, zone=128:
  fail 1.000000

min_rewrite=0.05, zone=32:
  +0.129568 bits/atom/pass
  count ledger +0.116873
  fail 0.500000

min_rewrite=0.05, zone=64:
  +0.097063 bits/atom/pass
  count ledger +0.084368
  fail 0.500000
```

## Interpretation

Stable prefix zones are parseable and avoid a bitmap, but the count ledger plus
geometry rigidity already exceeds the H124 raw-fallback margin. This closes the
most direct counted-zone repair unless a public threshold can derive counts
without storing them.

## Artifact

`model_analysis/birth_channel_research/H129-zone_prefix_raw_counts.py`
