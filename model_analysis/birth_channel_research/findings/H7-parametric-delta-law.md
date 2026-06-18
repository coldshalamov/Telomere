# Avenue H7 — public parametric delta/slack law

Author: Codex continuation with one read-only subagent derivation. Date:
2026-06-17.
Status: current closest paid Total-Cover witness mode in this branch.

## HYPOTHESIS

H5/H6 showed that high-arity Total-Cover is mostly paying for payload
width/slack:

```text
delta = arity * B - payload_width
```

The H6 exact suffix table still paid about `4.954` bits/record for delta, but
that might be table sparsity rather than real entropy. The raw first-hit law
under the uniform hash model gives a public analytic distribution for width.
If that law prices selected deltas well enough, it could be an honest witness
language with no per-file counts or hidden layout.

## MECHANISM

Runnable kernel:

- `../H7-total_cover_parametric_delta.py`

All modes keep Total-Cover semantics:

- every record opens by invariant;
- no birth/open/carry channel;
- no sparse cover map;
- no per-file model;
- arity is still paid by a public suffix arity model.

Delta modes tested:

```text
suffix  = H6-style P(delta | exact remaining, exact arity)
global  = public selected-delta table
arity   = public selected-delta table by arity
raw     = analytic first-hit width law
tilted  = raw first-hit law tilted by one public beta fit on train covers
```

The raw law comes from:

```text
R ~ Geometric(2^-L), where L = arity * B
payload_width W is the smallest Lotus width that can name R
delta = L - W
```

With `C(w)=2^(w+1)-3`, the exact public bucket mass is:

```text
Pr[W=w] = (1-q)^C(w-1) - (1-q)^C(w)
q = 2^-L
```

conditioned on the configured frontier `W <= D`.

## RESULT

`nearest-paid-miss(raw-delta-law)`

Bounded held-out rows at `B=4,K=128,D=512`:

```text
H7 all-mode comparison
  command: --train-trials 32 --eval-trials 16 --iterations 3
           --alpha 0.02 --modes global raw tilted

  global  gain = -0.026048 bits/input atom, delta = 3.498 bits/record
  raw     gain = -0.014672 bits/input atom, delta = 2.594 bits/record
  tilted  gain = -0.015688 bits/input atom, delta = 2.777 bits/record

H7 raw-only confirmation
  command: --train-trials 64 --eval-trials 32 --iterations 3
           --alpha 0.02 --modes raw

  paid gain      = -0.011929 bits/input atom
  missing        = 1.357 bits/selected record
  records/atom   = 0.008789
  avg arity      = 113.78
  rank bits/rec  = 453.542
  arity bits/rec = 0.520
  delta bits/rec = 2.407
```

This is the closest paid witness mode found in the H5-H7 line. It still does
not cross positive. To cross from the raw-only confirmation, a public selected-
delta model must save about `1.36` more bits/record without increasing arity or
rank cost.

## SUBAGENT DERIVATION

The raw asymptotic law is not near-deterministic. For large `L`:

```text
R / 2^L -> Exp(1)
delta -> 1 - ceil(log2 Exp(1))
```

and the limiting raw delta entropy is about `2.832` bits/record. Selection
tilts deltas upward because the DP prefers short payload widths, but the
residual should remain a lattice extreme-value/Gumbel-like variable unless a
new decoder-derived invariant determines width.

This matches H7: the analytic raw law cuts H6's sparse-table delta cost from
about `4.954` to about `2.4` bits/record, but it does not collapse below the
rough `~1.0` bit/record budget needed for positive paid compression.

## DECODER OBSERVATIONS

Open vs carry:

- Total-Cover has no carry. Every record opens.

Birth pass / salt:

- No birth pass is stored or needed in this branch.

Refresh:

- Fresh matches can be searched for the next total-cover layer.
- The witness stream still has to be shorter than the current layer.

Stored / derived / hidden info:

- `rank/payload` is paid as the seed witness.
- `arity` is paid by a public suffix arity model.
- `delta` is paid by a public analytic raw law in the best H7 mode.
- Any beta, table, or adaptive count chosen per file would be metadata. H7 only
  treats beta/tables as free when trained/frozen from independent public data.

## NEXT TARGET

The remaining target is narrower:

```text
Find a public selected-delta residual law that saves >= 1.36 bits/record
over the raw first-hit law at B=4,K=128,D=512, without losing match supply.
```

Promising but unproven variants:

1. A selected-extreme-value law conditioned on an effective local choice count
   `M_eff(remaining, arity)`.
2. A low-dimensional Gumbel/lattice law for selected delta residuals, fit on
   independent public samples and frozen by profile.
3. A canonical width rule that makes `payload_width` mostly decoder-derived.
   This must be checked carefully because forcing a width can throw away the
   same order-statistic advantage it tries to encode cheaply.

If those cannot reduce delta below roughly `1.0` bit/record while preserving
rank and arity costs, the high-arity Total-Cover line is effectively at the
uniform-source boundary under public stateless witness coding.
