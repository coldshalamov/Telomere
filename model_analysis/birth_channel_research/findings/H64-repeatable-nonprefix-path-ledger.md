# H64 - Repeatable Non-Prefix Path Ledger

Date: 2026-06-17

## Question

EOF/non-prefix coding can shrink almost every fixed-length input once. Could
that be the missing public invariant for repeatable stateless recursion?

H64 separates three cases:

```text
fixed exact shrink
variable shrink with the length path available
variable shrink where final bytes alone identify the inverse chain
```

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H64-repeatable_nonprefix_path_ledger.py
```

For `P` passes, minimum saving `s` per pass, and starting length `n`, every
honest stateless P-pass winner must end in a final string of length at most:

```text
n - P*s
```

So the final-output bound is:

```text
fraction <= (2^(n-P*s+1)-1) / 2^n ~= 2^(1-P*s)
```

If the length path is free, the apparent cover is:

```text
sum_{t=P*s..n} compositions(t,P,s) * 2^-t
```

For `s=1`, this tends to `1` as `n` grows, for every fixed `P`. That is exactly
why the idea looks promising. The missing channel is the per-pass length path.

## Representative Results

For `n=128,s=1`:

```text
P=1:  stateless variable fraction ~= 1.000000
P=2:  stateless variable fraction ~= 0.500000, path-free apparent ~= 1.000000
P=4:  stateless variable fraction ~= 0.125000, path-free apparent ~= 1.000000
P=8:  stateless variable fraction ~= 0.007812, path-free apparent ~= 1.000000
P=16: stateless variable fraction ~= 0.000031, path-free apparent ~= 1.000000
P=64: stateless variable fraction ~= 1.084e-19, path-free apparent ~= 0.535193
```

For `P=64`, finite starting length is already biting; the infinite-length
limit is `1`, but `n=128` has only enough headroom for `0.535193` apparent
coverage even with the path available.

The path selector is not small. For `n=128,P=64,s=1`, the path-free row has:

```text
average path bits ~= 114.186748
max path bits ~= 123.171434
bucket+path entropy bits ~= 118.681150
```

That is the exact bloat that was hiding in "just use final length/EOF".

## Verdict

EOF/non-prefix length coding is a real one-shot effect, and H64 explains why it
feels like it should recurse. But repeatability needs one of two things:

1. many possible length paths, which cover almost all inputs but cost a path
   selector; or
2. one public/canonical path, which is stateless but collapses the winning
   fraction exponentially as `2^(1-P*s)`.

So this does not solve roughly-all-data recursion over arbitrary passes. It
does give a precise target for any future final-board/EOF proposal: show how the
decoder derives the length path without either storing it or reducing coverage
to the final-output bound.
