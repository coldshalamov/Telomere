# H178 - Neutral Option Capacity

## Conjecture

Near-equal witness lookahead is legal Telomere machinery, but it is an option
channel. If a current interval has `H` same-cost matching witnesses, choosing
the future-fertile seed is free only because that seed is already emitted. The
free steering capacity is at most:

```text
log2(H)
```

For near-equal witnesses, extra slack/bloat buys more options, but the same
bits are paid in the current layer.

## Model

`H178-neutral_option_capacity.py` combines the H177 total-cover edge law with a
fantasy conversion bound:

```text
lambda = Kraft(arity) * 2^(-s)
option = E[log2(H) | H > 0], H ~ Poisson(lambda)
fantasy_net = s + option
```

where `s` is current paid gain per record. Negative `s` is bloat.

It also samples full-cover path support, so a tiny local option surplus cannot
hide bad tails.

## Results

Representative rows:

| row | path support | option bits | current gain | fantasy net | reading |
| --- | ---: | ---: | ---: | ---: | --- |
| V1 `K5,N128,s=-8` | 1.000 | 7.804135 | -8.000000 | -0.195865 | high support, negative even under fantasy conversion |
| V1 `K5,N128,s=-1` | 0.307 | 0.880294 | -1.000000 | -0.119706 | still negative and poor support |
| fixed `K8,N128,s=-1` | 0.709 | 1.000389 | -1.000000 | +0.000389 | tiny fantasy surplus, bad full-cover tail |
| fixed `K8,N128,s=-2` | 0.990 | 1.838796 | -2.000000 | -0.161204 | support mostly repaired, negative |
| fixed `K128,N128,s=-1` | 0.106 | 1.000389 | -1.000000 | +0.000389 | high arity worsens path tail at this length |
| fixed `K128,N128,s=-8` | 1.000 | 7.997182 | -8.000000 | -0.002818 | asymptotically almost break-even, not positive |

The only positive fantasy row is the fixed-code `s=-1` knife-edge, and it has
insufficient full-cover support. Rows with estimated path support above `0.95`
are negative before parser, fallback, or multi-pass losses.

## Bill

Same-cost choice is free only for the chosen emitted seed. Non-emitted cloud
mass, post-hoc profiles, route choices, or future-score ranks are selectors and
must be charged.

Weighted neutral lookahead bound:

```text
usable dividend <= log2(sum_c 2^-delta(c))
```

where `delta(c)` is each candidate's extra current cost relative to the
equal-cost baseline.

## Mutation

Do not spend more broad search on neutral lookahead alone. It can still be a
component of a future mechanism, but only after another mechanism supplies:

- stable full-cover support without large bloat;
- a real public recurrent fertility law; or
- a generated/reachable source regime whose tax is acknowledged.
