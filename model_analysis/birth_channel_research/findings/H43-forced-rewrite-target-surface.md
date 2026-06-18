# H43 - forced-rewrite / near-total-cover target surface

Date: 2026-06-17

## Question

What exactly must be true for the user's all-block replacement idea to flip
positive?

The branch is:

```text
every pass rewrites every atom, or almost every atom
every output unit is a record
every record opens during decode
```

This removes open/carry and birth-pass entropy by invariant. H43 prices what is
left.

## Unit correction

There are two different "2 bits" discussions:

1. **Current high-arity Total-Cover rows:** savings are per selected record.
   H7 has only `0.008789` records/input atom, so `2 bits/record` is only
   `0.017578 bits/input atom`.
2. **Future all-atom rewrite premise:** a mechanism gives paid margin per
   rewritten input atom. That is much stronger and can tolerate more
   exceptions.

Do not mix these units.

H43 rows:

```text
H7 raw first-hit delta:
  records/atom = 0.008789
  2 bits/record -> 0.017578 bits/atom
  current miss = 1.357 bits/record = 0.011927 bits/atom

H9 fixed slack 0:
  records/atom = 0.009765
  current miss = 1.261 bits/record = 0.012314 bits/atom

H12 perfect-credit upper bound:
  current miss = 0.746 bits/record = 0.008196 bits/atom
```

## Current record-level exception budget

If the current H7-style record density is the unit, the exception ledger must
be tiny. For H7:

```text
surplus=1.357 bits/record:
  P=64:   max eps = 0.00066343
  P=256:  max eps = 0.00059161
  P=4096: max eps = 0.00048794

surplus=2.000 bits/record:
  P=64:   max eps = 0.00101211
  P=256:  max eps = 0.00089885
  P=4096: max eps = 0.00073709
```

So for the current high-arity rows, "near total" means much more than 99%.
It means roughly `99.9%+` if the exception ledger is charged against
record-level surplus.

## Optimistic all-atom rewrite premise

If a new mechanism truly gives `g` paid bits per rewritten input atom, the
condition is:

```text
net = (1-eps) * g - H2(eps) - eps * log2(P-1) - eps * F > 0
```

where `F` is fallback overhead per exception atom above raw.

H43 rows for `g=2 bits/atom`:

```text
F=0:
  P=64 coverage > 83.135%
  P=256 coverage > 85.869%
  P=4096 coverage > 89.234%

F=3:
  P=64 coverage > 86.887%
  P=256 coverage > 88.557%
  P=4096 coverage > 90.835%

F=8:
  P=64 coverage > 90.348%
  P=256 coverage > 91.262%
  P=4096 coverage > 92.634%
```

This validates the intuition that near-total cover can make metadata cheap,
but only after the paid per-atom rewrite margin exists.

## Option-count dividend

The user's "15 options at K=5" intuition is real. An interior atom participates
in:

```text
M = 1 + 2 + ... + K = K(K+1)/2
```

possible intervals. The ideal independent best-of-options dividend is:

```text
K=5:   M=15,   log2 M=3.907 bits
K=16:  M=136,  log2 M=7.087 bits
K=64:  M=2080, log2 M=11.022 bits
K=128: M=8256, log2 M=13.011 bits
```

That dividend is the right reason to keep studying higher arity. It still must
survive non-overlap constraints and the paid witness stream.

## Coverage vs compression

Coverage and compression are different:

```text
coverage:    every atom has at least some matching interval
compression: the chosen paid witness is shorter than raw
```

Coverage can be easy because arity-1 spans dominate the "has any match" event.
For one specific `k`-atom span, however, `D` must sit near `k*B` to get a hit:

```text
B=4,k=5:    span=20 bits, 90% hit at D=21.203
B=4,k=128:  span=512 bits, 90% hit at D=513.203
B=8,k=128:  span=1024 bits, 90% hit at D=1025.203
```

This is the search-depth meaning of larger bundles: they are reachable in
principle, but the witness length grows with the span unless a better public
cover code captures the option dividend.

## Verdict

The all-block branch correctly removes the birth/open problem. The remaining
target is not "find any match for every atom"; it is:

```text
make the paid witness margin positive
```

Current paid high-arity rows are still negative:

```text
H7 margin = -1.357 bits/record
H9 margin = -1.261 bits/record
H12 perfect-credit margin = -0.746 bits/record
```

The next best scientific test is a collective public cover distribution:

```text
Q(x) = sum over covers c expanding to x of 2^-L(c)
```

If normalized public `Q` still has uniform cross-entropy at or above raw as
`N,K,D` grow, the uniform paid Total-Cover branch is closed except for premise
changes such as source-shaped public interpreters or measured fertility lift.

## Artifact

`model_analysis/birth_channel_research/H43-forced_rewrite_target_surface.py`
