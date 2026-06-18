# H120 - Width-Channel Equivalence

Date: 2026-06-18

## Question

Can payload-width information be hidden in seed classes, self-synchronizing
syntax, or a checksum referee more cheaply than an explicit width stream?

Runnable artifact:

```text
model_analysis/birth_channel_research/H120-width_channel_equivalence.py
```

## Model

H120 reuses the exact selected width ledgers from H118 and prices the same
width sequence as:

- fixed width symbols;
- enumerative width stream;
- count-paid enumerative stream;
- optimal seed-class supply loss;
- prefix/self-synchronizing lower bound;
- trial-decode/checksum ambiguity.

If the selected width distribution is `p(w)`, a seed-class or prefix grammar
that makes width derivable pays at least:

```text
H(W) = sum_w p(w) log2(1 / p(w))
```

unless it changes the selected-width distribution itself or makes width public
from an independent invariant.

## Results

Using the same seed as H118 (`--seed 118001`), with 128 atoms, four passes,
eight trials, and `min_rewrite_raw_frac=0.25`:

```text
scale 1:
  local_delta/atom/pass       -0.055664
  enum/record                  4.360303
  seed_class/record            5.341012
  checksum64_records          14.677878
  total_enum/atom/pass        +0.101886
  total_seed_class/atom/pass  +0.137322

scale 1024:
  enum/record                  5.337140
  count_paid/record            5.345849
  entropy/record               5.341012
  seed_class/record            5.341012
  checksum64_records          11.991442
  total_enum/atom/pass        +0.137182
  total_seed_class/atom/pass  +0.137322
```

The default seed was similar but worse:

```text
scale 1024:
  enum/record                  5.603284
  count_paid/record            5.611633
  entropy/record               5.607107
  checksum64_records          11.421874
```

## Interpretation

This is the clean closure check for "hide the width symbol":

```text
explicit width stream ~= prefix/self-sync width grammar
                    ~= optimal seed-class supply loss
                    ~= checksum ambiguity bits
```

The finite scale-1 enumerative stream can look cheaper because the selected
sequence is short and count-shaped. At scale, it approaches the empirical width
entropy. A 64-bit checksum referee covers only about 12 width decisions at this
entropy, before any safety margin.

H120 also corrects the optimistic reading of H118. H118's `~2.26 bits/record`
number was a per-pass lower bound from repeating the same tiny ledger. When
independent selected edges are pooled, the boundary entropy is closer to
`5.3-5.6 bits/record`.

## Verdict

No candidate codec.

Seed classes, self-synchronizing syntax, terminators, and checksum trial-decode
do not change the accounting unless they reduce the actual selected-width
entropy or make width public by a priced invariant. This branch should stop
testing "where to hide width" and test mechanisms that change the width
distribution or public target-length geometry.
