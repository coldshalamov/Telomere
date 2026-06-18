# H146 - Slack Superposition Transfer

Date: 2026-06-18

## Question

Can the encoder intentionally choose a slightly larger replacement now because
that visible record string is more fertile on the next pass?

Runnable artifact:

```text
model_analysis/birth_channel_research/H146-slack_superposition_transfer.py
```

## Model

This is an exact tiny `B=1` model using H96's paid V1/J3D1 record family.
For each starting word `x`, the kernel enumerates every visible record-string
description `c` whose current length is within a slack budget:

```text
len(c) <= len(x) + slack
```

The decoder receives only `c`. Discarded alternatives are not stored, decoded,
or ranked. Three public choices are compared:

```text
cheapest-now: minimize len(c)
future-only:  maximize next-pass all-description saving of c
two-pass:     maximize current saving + next-pass saving
```

The same-length random control measures whether selected visible genotypes are
more fertile than arbitrary bit strings of equal length.

## Results

Default exact row:

```text
N=5,K=5,D=6
best coverage in tested slacks = 0.906250 at slack=12
two-pass total at slack=12 = -20.121189 bits/word
selected future-vs-random at slack=12 = -0.007808 bits
```

Focused rows:

```text
N=5,K=5,D=8,slack=10:
  coverage = 1.000000
  two-pass total = -19.570534 bits/word
  lift over cheapest-now = 0.000000 bits/word
  future-vs-random = -0.089661 bits

N=4,K=4,D=7,slack=12:
  coverage = 1.000000
  two-pass total = -21.202097 bits/word
  future-vs-random = +0.381631 bits

N=6,K=5,D=7,slack=14:
  coverage = 1.000000
  two-pass total = -29.390338 bits/word
  lift over cheapest-now = +0.141632 bits/word
  future-vs-random = +0.621127 bits
```

## Reading

The user's non-greedy point is real: choosing among valid visible descriptions
can produce a future-fertility signal, and no metadata is needed for discarded
alternatives.

The exact toy does not yet rescue compression. Full-coverage rows remain far
negative after current bloat, and the measured lift is sometimes only a
same-length visible-string effect rather than a stable advantage over random
controls.

## Verdict

Slack superposition is a live research target, but not a solution in the exact
tested family. The next constructive test must replace the collective
next-pass saving score with an actually selected recurrent record stream and
show a same-budget random-control lift large enough to meet the H144
`0.008625-0.040116` bits/atom/candidate target.
