# H94 - Normalized Rank Witness Sweep

Date: 2026-06-17

## Question

H92 crossed only when high-arity seed ranks of Lotus payload width `w` cost
exactly `w` bits. That is not a prefix-safe per-record witness code: every
width class contributes about one full Kraft unit.

Can a custom arithmetic rank or arity+rank record code honestly recover the
H92 crossing without paying full J3D1?

Runnable artifact:

```text
model_analysis/birth_channel_research/H94-normalized_rank_witness_sweep.py
```

## Modes

```text
h92_lower:
  K<=5 exact V1; K>5 fixed_arity_bits + payload_width.
  Lower bound only; high-arity seed-width classes are not normalized.

custom_rank:
  fixed_arity_bits + -log2(p_rank)
  p_rank proportional to 2^-payload_width over the public frontier.

custom_record:
  -log2(p(arity,rank))
  p proportional to 2^-fixed_arity_bits * 2^-payload_width over legal records.

paid_lotus:
  K<=5 exact V1; K>5 fixed arity bits + J3D1(payload_width).
```

## Result

Only the underpriced lower bound crosses:

```text
mode           best collective row        log2 Z_total
h92_lower     K=8, D=12                   1.001339
custom_rank   K=8, D=10                  -2.188694
custom_record K=6, D=12                  -1.781751
paid_lotus    K=12, D=12                 -5.301885
```

The `custom_rank` result is independent of `D` for fixed `K` in the reported
rows because the rank distribution is normalized over the public frontier. More
seed ranks add possibilities, but they also add rank-code mass that must be
paid.

## Reading

H94 closes the most natural middle ground between H92 and H93. A custom
arithmetic witness code can be much cheaper than paid J3D1, but it still has to
pay the seed-width multiplicity. In this toy, that bill removes the H92 crossing.

## Verdict

The H92 crossing is not rescued by normalized rank or record arithmetic coding.

The remaining route is not "better width coding" by itself. A successful
mechanism must change the generated span law, create real neutral/developmental
fertility, or add a paid public invariant that increases honest witness Kraft
mass without reintroducing a selector/profile channel.
