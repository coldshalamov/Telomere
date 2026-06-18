# H162 - Item-Stream Full-Cover DP

Date: 2026-06-18

## Question

Does the H161 local item-level opportunity survive when the encoder must cover
an entire current item stream with non-overlapping source records?

Runnable artifact:

```text
model_analysis/birth_channel_research/H162-item_stream_cover_dp.py
```

## Model

The target layer is sampled from the normalized public item-grammar mass. For
each interval of `1..K` target items, H162 samples the exact best matching source
record cost under the uniform hash law and exact J3D1 source costs.

```text
edge exists       = at least one source seed matches the interval bytes
edge cost         = shortest matching source record cost
full cover        = min-cost DP over non-overlapping edges
failure           = no complete record cover exists
```

Failure is not harmless. Under the strict Total-Cover branch there are no carry
records, sparse maps, or repair ledgers, so a failed cover needs a new paid
fallback channel.

## Results

Strict `seed_only`, current V1/J3D1 `K=5`, `B=8`, 1000 trials:

```text
D   N   support  edgeHit   inBits      outBits     gain/item
40  16  0.268    0.327379  308.302239  388.093284 -4.986940
40  32  0.077    0.312337  624.415584  781.025974 -4.894075
56  16  0.319    0.396282  371.517241  441.373041 -4.365987
56  32  0.109    0.391271  729.577982  865.302752 -4.241399
80  16  0.585    0.494107  466.558974  533.589744 -4.189423
80  32  0.310    0.475063  931.493548 1063.016129 -4.110081
```

`mixed_all` improves support and the successful-cover sign slightly, but it
spends literals and therefore is not the strict maintained-freshness row:

```text
D   N   support  edgeHit   inBits      outBits     gain/item
40  16  0.364    0.394303  266.912088  333.464286 -4.159512
40  32  0.132    0.374825  542.484848  677.189394 -4.209517
56  16  0.433    0.473568  326.644342  387.575058 -3.808170
56  32  0.164    0.453663  656.981707  776.250000 -3.727134
80  16  0.617    0.571925  404.290113  461.400324 -3.569388
80  32  0.384    0.561225  805.760417  916.869792 -3.472168
```

## Reading

This directly tests the user's non-greedy concern in the current exact V1/J3D1
item grammar: the DP is free to choose interval boundaries after seeing the
whole sampled item stream, and it uses the best matching source cost for every
available interval.

The result is negative:

```text
successful strict covers still expand by about 4.1 to 5.0 bits/item
strict support is far below 1 even at D=80
mixed_all support comes partly from literals, which do not maintain freshness
```

So H161 was not a reward hack, but it was only a sparse local opportunity. The
full-cover DP turns that local opportunity into a sharper miss, not a crossing.

## Verdict

Current exact V1/J3D1 item-level non-greedy covering does not solve maintained
stateless recursion. The next version must change a priced knob:

```text
extended arity grammar with exact Kraft cost
custom total-cover item witness language
source-shaped/fertile public item distribution
or a paid repair channel whose cost is below the H162 miss
```

For the present branch, the nearest concrete target is not "first found versus
best found"; H162 already gives the cover DP the best available local choices.
The missing margin is several bits per item plus a large support gap.
