# Avenue H5/H6 — high-arity Total-Cover witness split

Author: Codex continuation with two read-only subagent checks. Date:
2026-06-17.
Status: current nearest-miss diagnostic for the Total-Cover branch.

## HYPOTHESIS

The best honest Total-Cover result is near flat because high arity amortizes a
small witness-stream deficit over many input atoms. The remaining question is
where that deficit lives:

```text
[arity][seed witness]
```

If most of the loss is in arity syntax, a better suffix/composition code might
cross. If it is in seed rank, the payload itself is the bill. If it is in
width/slack, then the target is a decoder-derived rule for seed-width selection.

## MECHANISM

Two new runnable ledgers test this.

- `../H5-total_cover_split_ledger.py`
- `../H6-total_cover_suffix_partition.py`

H5 reuses the current best public factored witness branch:

```text
context = remaining bucket
symbol  = arity under legal remaining mask
        + delta bucket where delta = arity * B - payload_width
        + exact seed rank/payload bits
```

and splits paid bits into:

```text
rank bits / record
arity bits / record
delta bits / record
```

H6 tests the concrete proposed improvement:

```text
P(arity | exact remaining atoms)
P(delta | exact remaining atoms, exact arity)
```

The H6 model is public/frozen, trained only on independent uniform-law
Total-Cover samples, then evaluated on held-out samples. It stores no per-file
counts, no transition table, no final layout, and no birth/open metadata.

## RESULT

`partial(refuted-as-crossover, useful-as-diagnostic)`

Bounded diagnostic runs at the live high-arity target `B=4,K=128,D=512`:

```text
H5 public factored split
  command: --train-trials 32 --eval-trials 16 --iterations 3
  paid gain      = -0.067796 bits/input atom
  free_arity     = -0.002112
  free_delta     = +0.008780
  free_stream    = +0.074463
  rank bits/rec  = 334.979
  arity bits/rec = 5.605
  delta bits/rec = 6.534

H6 exact suffix, alpha=0.02
  command: --train-trials 64 --eval-trials 16 --iterations 3 --alpha 0.02
  paid gain      = -0.040003 bits/input atom
  free_delta     = +0.006048
  free_stream    = +0.027344
  rank bits/rec  = 455.771
  arity bits/rec = 2.179
  delta bits/rec = 4.954
```

H6 improved the stream cost versus the rougher suffix run and confirmed the
subagent candidate was worth testing. It still did not cross positive. The
positive `free_delta` rows are not valid codecs; they show that the live bill is
the width/slack channel. Making delta free would be a hidden information
channel unless a new decoder-derived invariant determines it.

## COUNTING BOUND

The theorem gate remains:

For `N` atoms of `B` bits, any public uniquely decodable Total-Cover stream

```text
Y = ((arity_1, witness_1), ..., (arity_m, witness_m))
sum arity_i = N
```

obeys, on uniform `N*B`-bit inputs:

```text
Pr[L(Y) <= N*B - s] <= 2^-s
E[L(Y)] >= N*B
```

This already includes high arity, non-overlap DP, selected-rank bias, public
models, canonical tie-breaking, and suffix normalization. Those mechanisms can
move the loss toward zero, but a positive linear gain on roughly all uniform
inputs would violate Kraft/counting unless some assumption changes.

## DECODER OBSERVATIONS

Open vs carry:

- Total-Cover has no carry branch. Every record opens by invariant.

Birth pass / salt:

- No birth pass is needed inside this branch. A whole layer is decoded from the
  current record stream.

Refresh:

- Fresh search/frontier draws can be used on the next total-cover layer.
- The question is whether the next layer's public witness stream is shorter
  than the current layer.

Stored / derived / hidden info:

- `arity`: paid by public arithmetic code unless derived from suffix state.
- `rank/payload`: paid seed witness.
- `delta/slack`: paid width information; currently the tight bottleneck.
- `free_delta` is only a lower-bound diagnostic, not a lawful stream.

## NEXT TARGET

The only Total-Cover target still worth testing under uniform law is a stronger
public delta/slack invariant:

```text
Given exact remaining atoms and exact arity, can decoder derive or sharply
predict payload_width without transmitting ~5 bits/record?
```

Candidate tests:

1. Larger public training for H6 to estimate the asymptote of exact suffix
   tables.
2. Parametric delta law instead of sparse exact tables, so public smoothing is
   not wasting bits.
3. Canonical minimum-cover rule variants that make `payload_width` a function
   of arity and remaining state. Any such rule must be checked against hit
   density; forcing width deterministically may discard the order-statistic
   advantage it tries to save.

If those do not close the `~4-5 bits/record` delta bill, the high-arity
Total-Cover branch is probably at the uniform-source boundary. A true
breakthrough would then have to relax uniform/content-blindness or introduce a
new invariant that makes width/slack decoder-derived without sacrificing
matching supply.
