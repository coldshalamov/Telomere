# Avenue H2 — Total-Cover and the uniform-source boundary

Author: Codex continuation. Date: 2026-06-17.
Status: current addendum tying the Total-Cover witness search back to the
birth-channel conservation theorem.

## HYPOTHESIS

Total-Cover genuinely solves one hard problem: every record is born in the
current pass, so the decoder does not need open/carry, birth-pass tags, sparse
maps, final positions, or PCTB ledgers. The remaining question is whether the
selected `[arity][seed witness]` stream can be paid cheaply enough to keep
positive compression under a uniform, content-blind hash law.

Expected outcome: the free-boundary oracle can cross because it omits part of
the witness description, but every honest public parseable witness stream must
obey the same uniform-source counting bound as any other lossless code.

## MECHANISM

Total-Cover record:

```text
[arity][seed witness]
```

Decode reads records in order. Arity gives the previous-layer span length.
The seed witness names the exact hash expansion that reconstructs that span.
No pass history is stored or needed.

The tested paid witness families are in:

- `total_cover_lotus_crossover.py`
- `total_cover_public_model_kernel.py`
- `TOTAL_COVER_RESULTS.md`

The strongest current honest witness language is:

```text
arity under legal remaining-atom mask
+ width delta where delta = arity * B - payload_width
+ fixed/rank payload bits
```

with public model context derived from remaining atoms.

## RESULT

`partial(refuted-unbounded, nearest-miss=high-arity factored total-cover)`

Best current honest row:

```text
B = 4 bits
K = 128
D = 512 payload-width frontier
mode = public factored arity+delta model, remaining-atom context
gain = -0.0313 bits/input atom
records/input atom = 0.0089
avg arity = 112.22
missing = 3.518 bits/selected record
```

This is near-flat because one negative record is amortized over about 112 input
atoms. It is not positive. Larger arity reduces records per atom; it does not
make the selected record itself free.

## EVIDENCE

Evidence class: proven-by-math plus bounded statistical kernels.

Uniform counting theorem:

For any fixed public uniquely-decodable lossless code on `n`-bit inputs, at
most `2^(n-s)` codewords have length `<= n-s`. Therefore:

```text
Pr_uniform[L(X) <= n - s] <= 2^-s
E_uniform[L(X)] >= n
```

For the expectation statement, Kraft gives `sum_x 2^-L(x) <= 1`, and for a
uniform `X` over `2^n` inputs:

```text
E[2^-L(X)] <= 2^-n
2^-E[L(X)] <= E[2^-L(X)]   by Jensen, since 2^-x is convex
therefore E[L(X)] >= n
```

up to fixed/header or external-delimiter conventions. Those can shift an
`O(1)` constant, not create an unbounded or positive-rate compressor. This does
not depend on Telomere details. It is the master gate for any claim of positive
compression on roughly all arbitrary data.

Total-Cover specialization:

The selected witness sequence

```text
Y = ((arity_1,width_1,rank_1), ..., (arity_m,width_m,rank_m))
```

is a uniquely decodable description of the previous layer. If its paid length
is below the raw layer by `s` bits for most uniform layers, it violates the
counting theorem. The free-boundary oracle crosses only because it does not
fully encode `Y`.

Runnable ledger:

```powershell
python model_analysis\birth_channel_research\H2-uniform_counting_boundary.py
```

## CURRENCY

The bill appears in `stored bits` or `witness entropy`.

In the salted branch, birth pass is the missing coordinate:

```text
unpaid birth bill/record = log2(1 + (P - 1) * 2^-E)
```

where `P` is the number of candidate birth passes and `E` is any genuine
structural/free pruning under the independent wrong-pass survivor model.
Singles have `E = 0` in the current verdict, so the bill is `log2(P)` directly.
Bundle guards can have finite `E`, but the residual grows as `log2(P)-E` after
the knee.

Best finite-K salted candidate:

| arity | structure bits `E` | knee `2^E` | residual at `P=1e6` | bottleneck |
| ---: | ---: | ---: | ---: | --- |
| 2 | 9.36 | ~657 passes | ~10.58 bits/bundle | stored bits or DFS forks |
| 3 | 12.59 | ~6.2k passes | ~7.35 bits/bundle | stored bits or DFS forks |
| 4 | 14.97 | ~32k passes | ~5.01 bits/bundle | stored bits or DFS forks |
| 5 | 18.20 | ~301k passes | ~2.11 bits/bundle | stored bits or DFS forks |

This is the strongest finite-reach constructive branch: length-pinned bundles
can buy a large but finite pass window. It is not an all-data unbounded solution
because higher arity also spends `hit density / match supply`: exact `a`-block
matches are rarer under the uniform hash law.

In the Total-Cover branch, the birth bill is removed by invariant, but the
witness entropy bill remains:

```text
paid length = symbol stream bits + exact seed/rank bits
```

No hidden arrangement, checksum, final-board, or public-model selection channel
can be free unless it is decoder-derived and passes the same count.

Checksum pruning:

A fixed 64-bit checksum can prune at most 64 bits of global ambiguity because
those 64 bits are stored. It can make trial decoding practical for finite
ambiguity, but it cannot supply unbounded per-record birth or witness
information.

Unlimited compute:

Search can find rare lucky short descriptions when they exist. It cannot
increase the number of short descriptions in the public codebook. Therefore it
can spend time to select members of the `2^-s` lucky set, but it cannot make
that set contain roughly all uniform inputs.

## NEXT

The active target is no longer "find a free unbounded content-blind channel."
That is ruled out under the uniform hash law. The remaining constructive target
is finite:

1. quantify max-free-reach `K` for any bounded birth-pruning subsidy;
2. keep improving the public Total-Cover witness entropy rate to see how close
   it can get to zero loss;
3. identify the single assumption a true breakthrough must relax.

The assumption to relax is the uniform/content-blind source model. A non-uniform
public seed universe or biological-style interpreter can compress a non-uniform
source, but then the win comes from source bias/structure and must be priced as
such. Under uniform arbitrary data, a maintained positive expectation is
counting-forbidden.
