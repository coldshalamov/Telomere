# H122 - Public Gap Alphabet

Date: 2026-06-18

## Question

H121 used one fixed public gap and failed. What if a typed board makes target
length public, and records pay a small gap class instead of a full payload-width
symbol?

```text
T_pub = public target length
gap in public alphabet G
W = T_pub - gap
record = [arity][gap-class][W payload bits]
```

Runnable artifact:

```text
model_analysis/birth_channel_research/H122-public_gap_alphabet.py
```

## Model

H122 is still an optimistic typed-board lower bound:

```text
T_pub = actual interval bit length
```

A real codec must make that target length public by board geometry or pay the
missing `H(T)` channel.

The gap class is paid honestly:

```text
gap_bits = ceil(log2(number_of_gaps))
delta = arity_bits + gap_bits - gap
```

An edge is usable only when:

```text
payload_width <= T_pub - gap
```

So the test prices the tradeoff between:

```text
larger gaps = better per-record saving but lower match supply
more gaps    = better coverage but more class bits
```

## Results

At `min_rewrite_raw_frac=0.25`, `H114_raw_lower` still misses:

```text
gaps 4,5,6,8:
  +0.005469 bits/atom/pass
  fail 0.843750

gaps 4,6,8,10:
  0.000000 bits/atom/pass
  fail 0.843750
```

The optimistic `public_lane_raw` lower bound can produce negative finite rows,
but only by failing most trials:

```text
gaps 4,5,6,8:
  -0.002686 bits/atom/pass
  fail 0.750000

gaps 4,6,8,10:
  -0.015625 bits/atom/pass
  fail 0.843750
```

Wider alphabets improve coverage but give the savings back through gap bits and
padding:

```text
public_lane_raw, gaps 1,2,4,8:
  +0.011230 bits/atom/pass
  fail 0.250000

public_lane_raw, gaps 1,3,5,8,12:
  +0.008464 bits/atom/pass
  fail 0.062500

public_lane_raw, gaps 1,2,3,4,5,6,8,10:
  +0.001674 bits/atom/pass
  fail 0.125000
```

The last row is the nearest H122 miss, but it is still positive and still has
nonzero failure.

## Interpretation

Gap alphabets are a real improvement over one fixed gap. They let the DP spend
small gaps for coverage and use large gaps for savings. But the honest class
bits and padding/supply tradeoff still dominate.

The negative finite rows are not valid candidates because the branch requires
zero stale exceptions under maintained refresh. A failed trial would need a
fallback/literalization ledger, and prior H115 expiry rows showed that bill
pushes the branch positive.

## Verdict

No candidate codec.

The next route cannot simply be "more gap choices." To move this branch, a
mechanism must make the selected gaps strongly predictable from public geometry
while still preserving enough high-gap match supply, or it must change the
search objective so selected intervals naturally concentrate in a low-entropy,
high-saving gap class without hidden selection metadata.
