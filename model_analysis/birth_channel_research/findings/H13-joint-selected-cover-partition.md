# Avenue H13 - joint selected-cover partition code

Author: Codex continuation with read-only subagent audit. Date: 2026-06-17.
Status: raw/tilted semi-Markov partition check after H12.

## HYPOTHESIS

Previous Total-Cover witnesses paid arity and width mostly as independent
record fields. H13 tests whether the whole selected cover can be coded as one
canonical object:

```text
shape = [(arity_1, width_1), ..., (arity_m, width_m)]
```

with starts implied by cumulative arity. Exact seed residual remains paid as
`width` bits per selected record.

## MECHANISM

Runnable kernel:

- `../H13-joint_selected_cover_partition.py`

The public shape model is a normalized semi-Markov partition code:

```text
q(shape) = product_j psi(remaining_j, arity_j, width_j) / Z(N)

paid_bits = sum_j width_j + log2 Z(N) - sum_j log2 psi_j
```

The tested potential is:

```text
log2 psi = log2 P_raw(width | arity*B, width <= D)
         + beta * (arity*B - width)
         + record_bias
```

`beta` and `record_bias` are free only as frozen public profile constants.
Choosing them per file or from held-out rows would be metadata.

## ACCOUNTING FIX

The H13 audit found a shared sampler issue in
`../../total_cover_lotus_crossover.py`: the old helper
`lotus_payload_width_from_log_rank()` undercounted exact Lotus/J3D1 payload
width at bucket boundaries, e.g. rank `2` needs width `2`, not width `1`.

The sampler now uses exact integer-rank accounting:

```text
payload_width = ceil(log2(rank + 3)) - 1
```

implemented as `lotus_payload_width_from_rank(rank)`. The post-fix sanity
check gives:

```text
rank:  1 2 3 4 5 6 7 8 9 13 14
width: 1 2 2 2 2 3 3 3 3 3  4
```

This correction makes future Total-Cover rows stricter. Earlier rows that used
the shared sampled `lotus_payload_width` should be treated as optimistic unless
rerun. H9 fixed-slack rows are less affected because they derive width from
arity and test `edge.log2_rank <= W`.

## RESULT

`refuted-as-crossover`

First raw/tilted partition smoke without record-count bias was far from the
frontier:

```text
N=128, train/eval=8/4
best beta 1.0 -> -0.660436 bits/input atom
```

Adding a public `record_bias` correctly lets the model favor high-arity covers
and returns H13 to the near-miss regime:

```text
command:
python model_analysis\birth_channel_research\H13-joint_selected_cover_partition.py ^
  --atoms 128 --train-trials 24 --eval-trials 16 ^
  --betas 0.25 0.5 0.75 --record-biases -14 -12 -10 -8
```

| beta | record bias | train gain/atom | eval gain/atom | missing bits/rec | rec/atom | shape bits/rec |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.25 | -10 | -0.021747 | -0.013471 | 1.533 | 0.008789 | 4.310 |
| 0.50 | -12 | -0.022968 | -0.013879 | 1.579 | 0.008789 | 4.357 |
| 0.50 | -10 | -0.021729 | -0.013941 | 1.586 | 0.008789 | 4.364 |

The honest train-selected public-profile row is `beta=0.5`,
`record_bias=-10`, with held-out `-0.013941` bits/input atom. The best
held-out diagnostic row is `beta=0.25`, `record_bias=-10`, at `-0.013471`.

Same-seed post-fix baselines:

```text
H7 raw first-hit delta -> -0.012528 bits/input atom
H9 fixed slack 0      -> -0.026809 bits/input atom
```

So H13 beats this N=128 H9 fixed-slack row but does not beat H7, and it does
not cross positive.

## ACCOUNTING TRAPS CLOSED

- H13 pays `log2 Z(N)` over the full public shape space, not just feasible
  edges observed by the encoder.
- Exact seed residual is still paid as `width` bits per selected record.
- Train-selected `beta`/`record_bias` is the only honest profile row; best
  held-out rows are diagnostic.
- All reported rows have full cover.
- The record-count bias is included in both `psi` and `Z`; it is not a free
  preference for fewer records.

## NEXT

The raw/tilted semi-Markov partition code is not the missing mechanism. The
only joint-cover refinement still plausibly distinct from H7 is a genuinely
trained public CRF with small features such as remaining bucket, arity bucket,
delta bucket, and previous arity bucket, trained on independent uniform-law
covers and evaluated held-out. If that cannot save about `1.3` bits/selected
record, the joint-cover witness-code branch is likely exhausted under the
uniform-law Total-Cover model.

