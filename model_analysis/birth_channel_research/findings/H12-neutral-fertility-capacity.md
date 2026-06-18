# Avenue H12 - neutral witness multiplicity capacity

Author: Codex continuation with read-only subagent audit. Date: 2026-06-17.
Status: recursive-fertility capacity check after H11.

## HYPOTHESIS

H9's fixed-width Total-Cover mode is stateless but misses by about `1.2-1.3`
bits per selected record in stronger runs. One biology-shaped escape is
neutral multiplicity: if several same-width seeds reproduce the same span, the
encoder can choose among those witnesses without changing decode length.

That choice might make the next compressed layer more fertile while the current
record is still only:

```text
[arity][seed witness]
```

## MECHANISM

Runnable kernel:

- `../H12-neutral_fertility_capacity.py`

For a selected record with target length `L` and fixed witness width `W`, the
number of matching seeds in the same witness bucket is modeled as:

```text
M ~ Binomial(2^W, 2^-L) | M >= 1
  ~= Poisson(lambda=2^(W-L)) | M >= 1
```

The neutral capacity is:

```text
neutral_bits = E[log2(M) | M >= 1]
```

Those bits are not immediate compression savings. They are only an optimistic
future-fertility capacity. The diagnostic `perfect credit` row pretends every
neutral bit saves one future bit, which is the most generous uniform-law
accounting this mechanism can get without a real two-layer proof.

## RESULT

`refuted-as-simple-capacity-crossover`

Small smoke:

```text
command:
python model_analysis\birth_channel_research\H12-neutral_fertility_capacity.py ^
  --train-trials 8 --eval-trials 4 --iterations 2 ^
  --slacks -8 -6 -4 -3 -2 -1 0

best perfect-credit row:
slack -8 -> -0.008712 bits/input atom, residual 0.743 bits/record
```

Stronger bounded check:

```text
command:
python model_analysis\birth_channel_research\H12-neutral_fertility_capacity.py ^
  --train-trials 24 --eval-trials 16 --iterations 3 ^
  --slacks -8 -6 -4 -2 0
```

| slack | gain/atom | missing bits/rec | neutral bits/rec | perfect credit gain/atom | residual miss/rec |
| ---: | ---: | ---: | ---: | ---: | ---: |
| -8 | -0.050155 | 4.565 | 3.819 | -0.008196 | 0.746 |
| -6 | -0.045826 | 4.171 | 3.162 | -0.011083 | 1.009 |
| -4 | -0.039478 | 3.593 | 2.574 | -0.011198 | 1.019 |
| -2 | -0.026295 | 2.393 | 1.306 | -0.011946 | 1.087 |
| 0 | -0.026007 | 2.316 | 0.507 | -0.020313 | 1.809 |

Even the most generous perfect-credit upper bound stays negative. Buying more
neutral choice by allowing bloating witnesses increases the paid record cost at
roughly the same rate as the neutral capacity, leaving about `0.75` bits/record
unpaid in the best bounded row.

## ACCOUNTING TRAPS CLOSED

- Choosing among same-width matching seeds is stateless if the decoder only
  reads the chosen witness and all choices expand to the same previous span.
- The decoder is not assumed to know `M`, a rank among the `M` choices, or a
  per-file selection rule.
- `neutral_bits` are not counted as current compression. They are only a
  capacity upper bound for possible downstream shaping.
- Under the uniform law, one neutral bit can save at most one future bit in
  expectation. If a later two-layer kernel extracts more than that, it is using
  an unpriced channel or a non-uniform source.

## NEXT

The simple neutral-reservoir version is not the missing piece. A stronger
recursive-fertility claim would need an actual two-layer stateless kernel whose
held-out paid savings exceed this neutral-capacity ledger. The better immediate
target is H13: a joint selected-cover code that prices the whole cover as one
normalized public object, with exact seed residual still paid.

