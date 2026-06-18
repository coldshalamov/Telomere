# H71 - Finite-Pass Coverage Frontier

Date: 2026-06-17

## Question

What is the sharpest possible finite-pass boundary for:

```text
repeatable stateless compression
maintained over many passes
on roughly all structure-free uniform data
```

This intentionally ignores Telomere mechanics and gives the best possible
lossless counting bound. If a Telomere variant beats this, it must identify a
public invariant outside the count, a non-uniform source law, or a paid side
channel.

Runnable artifact:

```text
model_analysis/birth_channel_research/H71-finite_pass_coverage_frontier.py
```

## Bound

For an injective lossless map from `n`-bit inputs to binary outputs, the
fraction of inputs that can finish at least `S` bits shorter is bounded by:

```text
prefix / self-delimiting public stream:  2^-S
EOF one-shot arbitrary strings:         2^(1-S) - 2^-n
```

The EOF row is the generous loophole: it allows any shorter output string and
assumes the old length is known outside the code. It is stronger than a
parseable Telomere record stream, so it is the right upper bound to use before
declaring a content-blind escape.

If a recursive scheme claims `s` bits/pass over `P` positive-saving passes on
coverage `c`, then:

```text
S = P*s
```

and the eligible uniform coverage falls as the number of shorter outputs runs
out.

## Max Positive-Saving Passes

For desired coverage `c`, the maximum total saving is:

```text
prefix Smax = -log2(c)
EOF Smax    = 1 - log2(c)
```

Representative output:

```text
coverage  prefix Smax   EOF Smax  prefix K@1  EOF K@1  prefix K@2  EOF K@2
0.999       0.001443   1.001443           0        1           0        0
0.990       0.014500   1.014500           0        1           0        0
0.900       0.152003   1.152003           0        1           0        0
0.500       1.000000   2.000000           1        2           0        1
0.100       3.321928   4.321928           3        4           1        2
```

So for `90%` of uniform inputs:

```text
>=1 bit/pass:
  prefix/self-delimiting stream: K = 0
  generous EOF one-shot bound:   K = 1

>=2 bits/pass:
  prefix/self-delimiting stream: K = 0
  generous EOF one-shot bound:   K = 0
```

This is the sharp finite `K` under the structure-free premise.

## Average Saving Over Many Passes

At fixed coverage, allowed average saving per pass goes to zero:

```text
coverage=0.90, P=16:
  prefix average <= 0.009500 bits/pass
  EOF average    <= 0.072000 bits/pass

coverage=0.90, P=64:
  prefix average <= 0.002375 bits/pass
  EOF average    <= 0.018000 bits/pass

coverage=0.90, P=1024:
  prefix average <= 0.000148 bits/pass
  EOF average    <= 0.001125 bits/pass
```

This rules out maintained positive-rate recursion on roughly all uniform
inputs, independently of Telomere implementation details.

## Source Lift Required

If a mechanism still claims high coverage at forbidden `P,s`, it must be
source-shaped. H71 reports the lift required. For `90%` coverage:

```text
P=16, s=1 bit/pass:
  S = 16
  prefix lift needed = 58982.4x
  EOF lift needed    = 29491.2x
  prefix KL deficit  = 13.931007 bits
  EOF KL deficit     = 13.031009 bits

P=64, s=1 bit/pass:
  S = 64
  prefix lift needed = 1.66021e19x
  EOF lift needed    = 8.30103e18x
  prefix KL deficit  = 57.131004 bits
  EOF KL deficit     = 56.231004 bits
```

That is not a Telomere win under the structure-free premise. It is the exact
amount of non-uniformity needed to make the forbidden coverage true.

## Verdict

H71 gives the finite-pass answer the goal asks for under the strict
`roughly all data, not reliant on structure` premise:

```text
max K at 90% coverage and >=1 bit/pass:
  prefix/public self-delimiting stream: 0
  EOF one-shot generous bound:          1
```

Therefore any maintained recursive solution over arbitrary `P` must change one
of the premises:

- introduce a genuine public invariant not counted as a shorter-output
  selector;
- pay a side channel and beat it elsewhere;
- or use a non-uniform source/fertility law.

Without one of those, more arity, salting, shuffling, final boards, checksum
referees, or all-block replacement can at most move constants inside the same
frontier.
