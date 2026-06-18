# H113 - Seed-Class Partial Refresh

Date: 2026-06-18

## Question

Can the user's even/odd seed rejection idea replace the explicit ready/carry
map in partial refresh?

Runnable artifact:

```text
model_analysis/birth_channel_research/H113-seed_class_partial_refresh.py
```

## Model

Use a visible public seed class:

```text
pass t uses seed class t mod 2
```

The decoder opens records whose seed witness is in the current class and carries
the other class. This removes the H2 ready/carry bitmap only if a two-epoch
age invariant is enforced:

```text
old cohort must be refreshed or literalized before parity aliases again
```

The class is not free. H113 widens the visible global witness by `class_bits`
and charges exact J3D1 or fixed-delta syntax on the widened payload. Rows with
many live epochs add the residual age entropy.

## Result

Default grid:

```text
best J3D1 + H2 map:
  B4_K32_D128, slack=4, q>=0.50 -> +1.079422 bits/atom

best J3D1 + parity 2-epoch:
  B4_K32_D128, slack=4, q>=0.50 -> +0.109375 bits/atom

best fixedD + parity 2-epoch:
  B4_K32_D128, slack=2, q>=0.50 -> +0.046875 bits/atom

best local + parity 2-epoch:
  B4_K16_D64, slack=1, q>=0.50 -> -0.216797 bits/atom
```

Targeted broad check with 32-trial repeats:

```text
B4_K32_D128 fixedD+parity, slack=2, q>=0.50:
  +0.023438 bits/atom

B4_K128_D512 fixedD+parity, slack=8, q>=0.50:
  +0.041504 bits/atom

B6_K64_D384 fixedD+parity, slack=4, q>=0.50:
  +0.059722 bits/atom
```

Static parity without the two-epoch invariant fails: 64 live epochs either need
six seed-class bits or leave five residual age bits per record.

## Verdict

The seed-class idea is real and useful, but bounded. It is not a free many-pass
birth channel. It can replace the H2 ready/carry map only in a forced two-epoch
geometry where old records cannot survive long enough to alias.

The paid parseable branch became a near miss: `+0.023438` bits/atom. The live
remaining gap was no longer readiness; it was the width/delta stream. H114
therefore tested a frozen public delta law inside this parity geometry.
