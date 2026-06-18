# H117 - Parseable Payload-Width Symbols

Date: 2026-06-18

## Question

H116 still used the H114/H115 delta symbol:

```text
delta = target_bits - payload_width
```

That is parseable for fixed atoms because `target_bits = arity * B` is known
after reading arity. In a heterogeneous record stream, the decoder generally
does not know `target_bits` until after it has read and expanded the seed.

Can the branch survive if the witness stream codes the payload width itself?

Runnable artifact:

```text
model_analysis/birth_channel_research/H117-parseable_width_symbol.py
```

## Model

H117 keeps H116's forced two-epoch transition, but the record grammar is now:

```text
[arity][payload-width symbol][payload bits]
```

This is parseable without knowing the generated target span length first.
`delta` mode remains in the script only as a labeled comparison.

## Results

Quick 96-atom public width-symbol rows:

```text
H114_raw_lower, global:
  +0.007076 bits/atom/pass
  rewrite_frac 0.072266

H114_raw_lower, arity:
  +0.016361 bits/atom/pass
  rewrite_frac 0.116536

H114_raw_lower, lane_due_arity:
  +0.003676 bits/atom/pass
  rewrite_frac 0.050781
```

Focused 128-atom repeat:

```text
H114_raw_lower, lane_due_arity:
  +0.007218 bits/atom/pass
  rewrite_frac 0.124268
```

Public-lane lower-bound rows with the visible class bit removed also miss:

```text
public_lane_raw, global:
  +0.023626 bits/atom/pass

public_lane_raw, lane_due_arity:
  +0.008773 bits/atom/pass

public_lane_raw, target_lane_arity hidden:
  +0.009548 bits/atom/pass
```

The near-flat rows are sparse. When a meaningful rewrite fraction is forced:

```text
H114_raw_lower, lane_due_arity, min_rewrite_raw_frac=0.25:
  +0.061297 bits/atom/pass

H114_raw_lower, lane_due_arity, min_rewrite_raw_frac=0.50:
  no finite path in the small sweep
```

## Interpretation

The honest parseable width stream is closer than the delta bucket rows at very
low refresh density, but the closeness comes from doing little work. It does
not maintain a high fresh-match rate. Once the DP is required to rewrite enough
raw material to plausibly sustain recursive match pressure, the row expands
strongly.

H117 also tightens the H115/H116 accounting language:

```text
delta coding is not enough for heterogeneous record streams unless target_bits
is made decoder-visible or separately encoded
```

Encoding `target_bits` or a target-length bucket would be an additional paid
channel, and H116's hidden target diagnostics already failed before charging
that channel.

## Verdict

No parseable candidate codec yet.

The best current honest row is a sparse near-miss:

```text
H114_raw_lower, lane_due_arity, width symbol:
  +0.007218 bits/atom/pass
```

But it rewrites only about `12%` of raw bits. The next target should not be
"better delta buckets"; it should be either:

```text
1. a collective width/record stream that stays parseable and amortizes over
   many selected records without a per-file hidden histogram; or
2. a public board/lane invariant that makes target-size class visible and pays
   the placement/supply cost.
```
