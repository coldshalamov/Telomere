# H161 - Item-Level Closure Economics

Date: 2026-06-18

## Question

Did H160 fail only because it used a bit-level H96 surrogate, while SPEC_V1
actually decodes records into self-delimiting items?

Runnable artifact:

```text
model_analysis/birth_channel_research/H161-item_level_closure_economics.py
```

## Model

Items:

```text
literal item = [111][B raw bits]
record item  = [arity][J3D1 seed witness]
```

A source record of arity `a` can match/decode to a target sequence of exactly
`a` items. H161 groups:

```text
target item sequences by visible length L
source records by visible cost c
```

For each `L`, it computes the expected best source cost under the uniform hash
law:

```text
Pr(best cost = c)
  = Pr(no cheaper source matches) * Pr(at least one cost-c source matches)
```

Modes:

```text
literal_only = target items are literals
mixed_all    = target items may be literals or records
seed_only    = target items are records only
```

`seed_only` is the strict maintained-freshness row. `mixed_all` is diagnostic
because literals can improve local closure while losing future seed freshness.

## Results

Strict seed-only B8/K5 arity-2 rows:

```text
D   seqK      seqTax    hitMass   accMass   saveMass  hit|seq       acc|seq       save|seq
16  0.067478  3.889432  0.002438  0.000084  0.000196  4.033e-08    3.041e-08    2.640e-07
24  0.098881  3.338166  0.022549  0.000138  0.000303  1.925e-10    1.264e-10    1.293e-09
32  0.131265  2.929449  0.050221  0.000181  0.000389  8.010e-13    5.361e-13    6.291e-12
40  0.151826  2.719510  0.075540  0.000205  0.000436  2.927e-15    1.869e-15    2.369e-14
48  0.173882  2.523815  0.100902  0.000225  0.000475  1.078e-17    7.224e-18    9.997e-17
56  0.197434  2.340555  0.122269  0.000243  0.000512  4.183e-20    2.960e-20    4.330e-19
64  0.219269  2.189226  0.141416  0.000260  0.000545  1.645e-22    1.135e-22    1.683e-21
80  0.245625  2.025472  0.179325  0.000276  0.000577  2.087e-27    1.396e-27    2.179e-26
```

`saveMass` and `accMass` are under the uniform bit law. `accMass` counts only
compressive accepted hits; `hitMass` also includes matches that are not shorter
than the target. `save|seq` is conditioned on the target already being a valid
seed-only item sequence.

Best default rows:

```text
seed_only, D=40, a=2:
  hitMass = 0.075540
  accMass = 0.000205
  saveMass = 0.000436
  seqK = 0.151826

seed_only, D=80, a=2:
  hitMass = 0.179325
  accMass = 0.000276
  saveMass = 0.000577
  seqK = 0.245625

mixed_all, D=40, a=2:
  hitMass = 0.164485
  saveMass = 0.000991
  seed item mass fraction = 0.757116
```

The B4/B8 seed-only rows are identical, as expected, because literal items are
excluded from `seed_only`.

## Reading

This is the first recent closed-language branch that shows a real positive
local opportunity again. Item-level closure changes the economics: a short
record can target multiple self-delimiting items whose visible length is much
larger than the source record.

But it is not a solution:

```text
positive saveMass is tiny
accepted compressive mass is much smaller than any-hit mass
save|seq is conditioned on valid item syntax
mixed_all spends literals that do not refresh future seed opportunities
```

The strict maintained-freshness row is `seed_only`. Its best tested uniform
saving mass is only `0.000577` at `D=80,a=2`, and the corresponding accepted
compressive mass is only `0.000276`. That is far below a maintained all-data
compression proof.

## Verdict

Item-level closure is alive as a target, unlike the H96 bit-level closed core.
The next required kernel is a full-cover item-stream DP:

```text
given a current item stream from the public item grammar,
choose non-overlapping source records over 1..K target items,
charge exact record costs,
measure whether expected per-item drift is negative
```

That will distinguish a sparse local opportunity from a maintained recursive
compression lattice.
