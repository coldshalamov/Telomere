# H200 - Nearest Generated-Cover Residual Ledger

## Conjecture

```text
Instead of using a fixed residual radius, choose the residual volume needed for
high coverage around many H198 generated roots.  Best-of-M generated roots may
reduce residual length enough to cover roughly all data.
```

This is the large-N analytic version of H199.

## Kernel

`H200-nearest_generated_cover_ledger.py`

Let:

```text
N = raw target bits
m = log2 effective generated phenotypes
V = residual family size
s = log2(V) - (N-m)
coverage ~= 1 - exp(-2^s)
```

For desired coverage `f`:

```text
log2(V) ~= N - m + log2(-ln(1-f))
```

The kernel prices four selected-root modes:

```text
free_index      = hidden root selector diagnostic
paid_index      = ideal lower bound, root costs m bits
native_fixed    = H198 fixed-pass root record, 27 bits for G=16,A=5
native_stored   = H198 stored-pass root record, 35 bits for G=16,A=5
```

It reports the short-path delta against raw `N`, hard one-bit fallback delta,
and implicit Kraft-fallback delta.

## Result

At the H198 best row scale:

```text
N=500000, m=16, coverage ~= 0.99, s=2.203

free_index:
  short_delta = -13.797000
  Kraft status = overfull

paid_index:
  short_delta = +2.203000
  hard_delta = +3.180952
  Kraft_delta = +2.184448

native_fixed:
  short_delta = +13.203000
  hard_delta = +14.070863
  Kraft_delta = +13.070864

native_stored:
  short_delta = +21.203000
  hard_delta = +21.990798
  Kraft_delta = +20.990798
```

Requested coverage rows for native H198:

```text
coverage=0.500: fixed short delta +10.471234, stored +18.471234
coverage=0.900: fixed short delta +12.203254, stored +20.203254
coverage=0.990: fixed short delta +13.203254, stored +21.203254
coverage=0.999: fixed short delta +13.788217, stored +21.788217
```

The default grid's best valid paid Kraft-fallback delta is still positive
expansion:

```text
native_fixed, m=16, s=-4, coverage=0.060587:
  Kraft_delta = +0.424750 bits
```

That row has low coverage; high coverage is much worse.

## Bill

Best-of-M roots buy `m` residual bits. A paid selected-root channel costs at
least `m`; native Telomere records cost `m` plus record overhead. Therefore:

```text
short_delta ~= root_cost - m + log2(-ln(1-f))
```

At 99% coverage, `log2(-ln(1-f)) ~= 2.203`, so even a perfect paid index expands
before syntax/fallback details.

## Mutation

Nearest generated-cover residuals do not solve roughly-all-data recursion. The
only crossing diagnostic is an unpaid `free_index`, which is exactly the hidden
root selector channel. Future residual work must supply a new recursively
generative residual law, not just a smaller residual around generated roots.

