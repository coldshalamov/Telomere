# H99 - Seed Parity Readiness Ledger

Date: 2026-06-18

## Question

Can seed rejection predicates such as even/odd seeds mark whether a record is
ready to open, avoiding an explicit birth/open channel?

Runnable artifact:

```text
model_analysis/birth_channel_research/H99-seed_parity_readiness_ledger.py
```

## Model

Use `C=2^g` public seed classes:

```text
pass t uses seed class t mod C
```

The decoder can read the seed class from the witness. The cost is not a visible
selector; it is match-supply loss:

```text
seed supply loss = g bits/record
```

If there are `P` live birth epochs, the residual ambiguity is:

```text
max(0, log2(P) - g)
```

So the total paid channel is:

```text
g + max(0, log2(P) - g)
```

## Result

Key rows:

```text
P live  g  C   paid  2-bit net  exact?
2       1  2   1.0   +1.0       true
4       2  4   2.0    0.0       true
8       3  8   3.0   -1.0       true
64      1  2   6.0   -4.0       false
64      6  64  6.0   -4.0       true
256     8  256 8.0   -6.0       true
```

## Reading

Even/odd seeds are a legal paid two-epoch discriminator. If every record lives
in only one of two possible birth epochs, one seed-class bit can replace an
explicit one-bit open/carry marker.

But carried records keep their seed class forever. One parity bit does not tell
the decoder which of many old passes produced the record. Across `64` live
epochs, exact seed-class birth marking needs `6` classes bits per record, paid
as a `64x` match-supply loss.

## Verdict

Seed rejection is a useful syntax channel, not a free readiness channel.

It is promising only for bounded two-epoch or near-total-exception designs where
the remaining live ambiguity is already tiny. It does not solve many-pass
stateless recursion by itself; it moves the birth/open bill into seed supply.
