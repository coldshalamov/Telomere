# H116 - Public Width-Law Search

Date: 2026-06-18

## Question

H115 showed that H114's fixed-atom crossing does not survive a real
variable-length record stream when every due old compact record must refresh.

Can a richer frozen width/delta law recover the local-width oracle while using
only facts the decoder knows before reading the seed witness?

Runnable artifact:

```text
model_analysis/birth_channel_research/H116-public_width_law_search.py
```

## Model

H116 keeps the H115 forced-refresh transition:

```text
literal/new/old items
age-1 records cannot be skipped
new records become age 0
skipped age-0 records become age 1
```

It changes only the context used by the frozen arithmetic-coded delta law.

Public contexts:

- `global`
- `arity`
- `start_mod_arity`
- `lane_due_arity`

Hidden diagnostic contexts:

- `target_arity`
- `target_lane_arity`
- `age_only`
- `composition`

The hidden contexts are not candidate codecs. They use target length or actual
interval age/literal composition before the decoder could know those facts.

## Results

Quick 96-atom public sweep:

```text
H114_raw_lower, global:          +0.031077 bits/atom/pass
H114_raw_lower, arity:           +0.008734 bits/atom/pass, fail 0.25
H114_raw_lower, start_mod_arity: +0.021417 bits/atom/pass
H114_raw_lower, lane_due_arity:  +0.010648 bits/atom/pass
```

Quick 96-atom hidden diagnostic sweep:

```text
H114_raw_lower, target_arity:      +0.028342 bits/atom/pass, fail 0.25
H114_raw_lower, target_lane_arity: +0.009967 bits/atom/pass, fail 0.25
H114_raw_lower, age_only:          +0.026526 bits/atom/pass, fail 0.25
H114_raw_lower, composition:       +0.036986 bits/atom/pass
```

Public-lane lower-bound rows with the visible class bit removed also stayed
positive:

```text
public_lane_raw, global:             +0.034470 bits/atom/pass, fail 0.25
public_lane_raw, arity:              +0.040205 bits/atom/pass
public_lane_raw, lane_due_arity:     +0.016450 bits/atom/pass, fail 0.25
public_lane_raw, target_lane_arity:  +0.011742 bits/atom/pass
```

Focused 128-atom repeats:

```text
H114_raw_lower, arity public:
  +0.023659 bits/atom/pass, fail 0.25

public_lane_raw, target_lane_arity hidden:
  +0.021842 bits/atom/pass, fail 0.125
```

## Interpretation

Simple public clocks do not replace the missing record-layer width channel.
More importantly, even the hidden target/age bucket diagnostics do not cross
under this frozen-count language. That means the failure is not just "the
decoder needs one obvious target-length bit"; the chosen public law is too weak
or too sparse for the heterogeneous due-refresh transition.

The H115 local oracle still matters:

```text
H114_raw_lower local oracle force_refresh:    -0.047175 bits/atom/pass
public_lane_raw local oracle force_refresh:  -0.085214 bits/atom/pass
```

So the geometry has option pressure, but H116 did not find a paid parseable
way to transmit enough of that choice.

Approximate remaining gap from the best focused public row:

```text
best public H116 row:     +0.023659 bits/atom/pass
H115 local oracle row:    -0.047175 bits/atom/pass
selected density:          0.020182 records/atom/pass
gap:                      ~3.51 bits/selected record
```

That is too large for one parity bit or a tiny lane clock. The next target
should either change the witness family, not merely the context model, or make
interval composition public through a real board/lane invariant and price the
placement supply loss.

## Verdict

H116 does not produce a candidate codec. It sharpens the live target:

```text
forced due-cohort refresh is viable only under the local-width oracle
simple frozen public width laws do not carry that oracle advantage
hidden target/age buckets are not enough in this language
```

Next work should move away from bucketed delta histograms and test either a
collective record-layer witness stream or a true public lane/board invariant
that makes due status and target-size class derivable without a per-file map.
