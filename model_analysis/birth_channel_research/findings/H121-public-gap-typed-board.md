# H121 - Public Gap Typed Board

Date: 2026-06-18

## Question

H119 fixed absolute width and missed. What if a public board makes target length
visible before the seed payload, so width can be a public gap?

```text
T_pub = public target length
W = T_pub - G
record = [arity][W payload bits]
```

Runnable artifact:

```text
model_analysis/birth_channel_research/H121-public_gap_typed_board.py
```

## Model

H121 is an optimistic typed-board lower bound. It sets:

```text
T_pub = actual interval bit length
```

That is only legal if a real board/type invariant lets the decoder know the
same length before reading the seed payload. If child composition is not public,
the missing `H(T)` channel must be charged and the row is invalid.

A candidate is usable when:

```text
payload_width <= T_pub - G
```

If selected:

```text
record_delta = arity_bits - G
```

So the width channel is gone, but match supply falls roughly like `2^-G`.

## Results

At `min_rewrite_raw_frac=0.25`, no tested gap found a finite due-refresh path:

```text
H114_raw_lower, gaps 1..16:
  fail 1.00 for every tested gap
```

With no rewrite floor, the DP chooses no records:

```text
gap 1..5:
  delta/atom/pass 0.000000
  sel/atom/pass   0.000000
```

At `min_rewrite_raw_frac=0.10`, rows expand or become fragile:

```text
H114_raw_lower, gap 4:
  +0.007812 bits/atom/pass
  rewrite_frac 0.121373
  supply_loss 2.892468 bits
  fail 0.125

H114_raw_lower, gap 5:
  0.000000 bits/atom/pass
  rewrite_frac 0.144043
  supply_loss 3.866910 bits
  fail 0.500
```

Removing the visible seed-class bit with the `public_lane_raw` lower bound does
not rescue it:

```text
public_lane_raw, gap 4:
  +0.007812 bits/atom/pass
  rewrite_frac 0.113281
  supply_loss 2.702092 bits
  fail 0.125

public_lane_raw, gap 5:
  0.000000 bits/atom/pass
  rewrite_frac 0.142578
  supply_loss 3.732262 bits
  fail 0.500
```

## Interpretation

This is a useful test because it gives the board the hardest part for free:
`T_pub` equals the true target length. Even then, the fixed public gap cannot
maintain refresh. Small gaps keep supply but do not save enough after arity;
large gaps save per hit but lose too many hits.

The mechanism is therefore not closed in all possible forms, but this simple
gap-locked typed board misses under a generous lower bound.

## Verdict

No candidate codec.

A future typed-board idea must add a new advantage beyond public target length:
for example, scheduled arity/slot types that concentrate real matches at a gap
that beats arity without losing due coverage. Merely setting
`W = T_pub - G` is not enough.
