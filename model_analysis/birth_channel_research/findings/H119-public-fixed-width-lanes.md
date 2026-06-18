# H119 - Public Fixed-Width Lanes

Date: 2026-06-18

## Question

H118 showed that selected payload widths carry about `2.26` bits per selected
record at meaningful forced-refresh density. Can the decoder avoid the width
channel by making payload width a public function of arity, lane phase, or item
position?

Runnable artifact:

```text
model_analysis/birth_channel_research/H119-public_fixed_width_lanes.py
```

## Model

Records use:

```text
[arity][fixed W(context) payload bits]
```

The width table is trained on independent local-oracle covers and then frozen
as a public profile constant. The decoder can parse width if `context` is
public.

Public contexts:

- `global`
- `arity_bucket`
- `exact_arity`
- `lane_exact_arity`
- `start_mod_exact_arity`

Hidden diagnostic context:

- `target_exact_arity`

Each edge is usable only if its sampled payload width is `<= W(context)`. The
record pays exactly `arity_bits + W(context)`, so the hidden price appears as
padding and match-supply loss rather than a width symbol.

## Sparse Rows

Without a rewrite floor, global fixed-width rows can look slightly negative:

```text
H114_raw_lower, global, q=0.50:
  -0.003906 bits/atom/pass
  sel/atom/pass 0.003906
  rewrite_frac 0.058594
  fail 0.50

H114_raw_lower, global, q=0.90:
  -0.003906 bits/atom/pass
  sel/atom/pass 0.001302
  rewrite_frac 0.037760
  fail 0.00
```

These are not maintained-refresh candidates. They are sparse "do almost
nothing" rows.

Public exact-arity and lane tables expand even in the no-floor sweep:

```text
H114_raw_lower, exact_arity, q=1.00:
  +0.009549 bits/atom/pass

H114_raw_lower, lane_exact_arity, q=1.00:
  +0.032118 bits/atom/pass
```

## Maintained-Refresh Rows

With `min_rewrite_raw_frac=0.25`:

```text
H114_raw_lower, global:
  no finite path for q=0.50/0.75/0.90/1.00

H114_raw_lower, exact_arity, q=0.50:
  +0.408854 bits/atom/pass
  fail 0.75

H114_raw_lower, lane_exact_arity, q=1.00:
  +0.109375 bits/atom/pass
  fail 0.75
```

Removing the visible seed-class bit with the `public_lane_raw` lower bound does
not rescue the idea:

```text
public_lane_raw, exact_arity, q=0.75:
  +0.039062 bits/atom/pass
  fail 0.75

public_lane_raw, lane_exact_arity, q=0.90:
  +0.020833 bits/atom/pass
  fail 0.75
```

Even the hidden target-size diagnostic misses:

```text
H114_raw_lower, target_exact_arity, q=0.90:
  +0.023438 bits/atom/pass
  fail 0.75
```

## Interpretation

Making width deterministic does remove the width-symbol entropy, but it buys
that by:

```text
1. rejecting too many otherwise useful matches; or
2. padding selected records to a width that spends the margin.
```

The hidden target-aware row missing is important. It means the failure is not
just "we need a clever public lane clock." In this fixed-width family, even
knowing a target-size bucket does not preserve enough match supply at meaningful
rewrite density.

## Verdict

No candidate codec.

Public fixed-width lanes close another obvious route around H118. The next
mechanism has to be less blunt than fixed `W(context)`: either a genuinely
self-synchronizing witness grammar, or a way to alter the search objective so
selected records naturally concentrate into one or two width classes without a
large padding/match-supply tax.
