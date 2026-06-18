# H118 - Collective Width Amortization

Date: 2026-06-18

## Question

H117's parseable width-symbol stream was close only when sparse. Could a
collective width stream amortize the payload-width metadata enough to make
forced due-cohort refresh negative at meaningful rewrite density?

Runnable artifact:

```text
model_analysis/birth_channel_research/H118-collective_width_amortization.py
```

## Model

H118 uses the H117 local-width oracle cover, then prices the selected payload
width sequence after the fact:

- `fixed`: each selected width costs `ceil(log2(D))` bits.
- `enum_free`: exact `log2 multinomial(width counts)` stream, count vector not
  charged.
- `enum_count_paid`: `enum_free` plus an exact positive-count vector/header.
- `enum_asymptotic`: same calculation with `--count-scale` used to repeat the
  empirical pass ledger and approach the large-file entropy rate.

This is a lower bound because selection is still made by the local oracle before
the collective width code is charged.

## Results

At 128 atoms, four passes, eight trials, forced `min_rewrite_raw_frac=0.25`:

```text
fixed:
  +0.197266 bits/atom/pass
  width_bits/record 7.000000

enum_free, scale 1:
  -0.005928 bits/atom/pass
  width_bits/record 1.376490

enum_count_paid, scale 1:
  +0.191922 bits/atom/pass
  width_bits/record 6.852116
```

The scale-1 `enum_free` crossing is not a stable amortized result. Repeating the
same empirical pass ledger drives the width-stream rate toward its entropy:

```text
enum_free, scale 16:
  +0.020897 bits/atom/pass
  width_bits/record 2.118872

enum_free, scale 256:
  +0.025503 bits/atom/pass
  width_bits/record 2.246363

enum_free, scale 1024:
  +0.025875 bits/atom/pass
  width_bits/record 2.256638
```

Exact count-paid rows converge to the same positive neighborhood:

```text
enum_count_paid, scale 64:
  +0.030400 bits/atom/pass
  width_bits/record 2.381870

enum_count_paid, scale 1024:
  +0.026359 bits/atom/pass
  width_bits/record 2.270043
```

The 256-atom local-oracle due-refresh rows failed for the sampled seeds, so the
finite-size evidence above should be treated as a lower-bound diagnostic, not a
production estimate.

## Interpretation

H118 closes the easiest collective-width loophole:

```text
short count-free enumerative streams can look negative
large-file/asymptotic width entropy is still too expensive
exact count metadata is not the only problem
```

The width histogram itself has about `2.26` bits/selected-record entropy in this
forced-refresh lower-bound row. At selected density about `0.036` records per
atom per pass, that width entropy alone costs roughly:

```text
0.036 * 2.26 ~= 0.081 bits/atom/pass
```

That spends the local-oracle margin.

## Verdict

No candidate codec.

Collective width coding is still a useful direction, but the missing mechanism
cannot be merely "store the selected width histogram once." It must either:

```text
1. reduce the actual width entropy of selected records;
2. make width nearly deterministic from public lane/board geometry; or
3. change the witness family so payload boundaries are self-synchronizing
   without paying about two bits per selected record.
```

## Follow-Up Correction

H120 later pooled independent selected-width ledgers and showed the boundary
entropy is closer to `5.3-5.6` bits per selected record. The `~2.26` number
above is an optimistic per-ledger repetition lower bound, not the final
large-file selected-width entropy.
