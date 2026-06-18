# H154 - Fixed-Cell Closure Phase

Date: 2026-06-18

## Question

Can stateless recursion be made easy by making every output unit a fixed-size
record cell, so every next layer is parseable by construction?

Runnable artifact:

```text
model_analysis/birth_channel_research/H154-fixed_cell_closure_phase.py
```

## Model

Every output cell has `C` bits and is always a record:

```text
[fixed arity bits][seed bits]
```

For `K` arities:

```text
A = ceil(log2 K)
W = C - A
```

A record of arity `a` expands to `a` input cells. Under the uniform hash law:

```text
p_a = 1 - (1 - 2^(-a*C))^(2^W)
```

Closure density is free: every output stream of whole cells parses on the next
pass. The price is match supply. H154 computes analytic per-cell interval
pressure:

```text
lambda = sum_a a * p_a
touch ~= 1 - exp(-lambda)
```

and runs a small full-cover interval DP over 128 cells. The simulation is only
a sanity check; the analytic touched/uncovered columns show whether the row is
powered.

## Results

Best rows from the tested grid:

```text
C=4,K=5:
  A = 3
  W = 1
  lambda = 0.138285
  touched per cell ~= 0.129149
  expected untouched cells in 128 = 111.468915
  full-cover success = 0.000000

C=8,K=5:
  A = 3
  W = 5
  lambda = 0.118701
  touched per cell ~= 0.111927
  expected untouched cells in 128 = 113.673362
  full-cover success = 0.000000

C=24,K=5:
  A = 3
  W = 21
  lambda = 0.117503
  touched per cell ~= 0.110862
  expected untouched cells in 128 = 113.809631
  full-cover success = 0.000000
```

Larger `K` makes the arity header wider and worsens the dominant arity-1
coverage:

```text
C=8,K=128:
  A = 7
  W = 1
  lambda = 0.007859
  expected untouched cells in 128 = 126.998037
```

## Reading

This is the cleanest "free closure" design: no open/carry, no birth pass, no
closure tax, and no final-board coordinates. But each record must fit its parser
and seed witness into one fixed cell. The seed supply then becomes too small to
cover arbitrary next-layer cells.

The dominant term is arity 1:

```text
p_1 ~= 2^(C-A-C) = 2^-A
```

Higher arities add very little because each extra cell in the target costs
another factor of `2^-C`.

## Verdict

Fixed-cell closure solves stateless parsing by spending the seed-address budget.
It is useful as a converse target:

```text
free closure + one-cell records => match starvation
```

A viable closed grammar would need to keep parseability while giving each record
more seed address space than a compressed cell can carry, which means the extra
space must be paid elsewhere or derived from a real public invariant.
