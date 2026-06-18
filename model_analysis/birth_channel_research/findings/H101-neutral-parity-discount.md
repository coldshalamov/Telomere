# H101 - Neutral Parity Discount

Date: 2026-06-18

## Question

H100 made the forced two-epoch target sharp:

```text
current pass births seed class t mod 2
decoder opens that class and carries the other class exactly once
```

Naively, this costs `1` bit/record because only half of the matching seeds are
allowed. But if a selected span has many matching seeds in the same witness
bucket, the encoder may be able to choose a seed with the desired parity at
less than a full one-bit supply penalty.

Runnable artifact:

```text
model_analysis/birth_channel_research/H101-neutral_parity_discount.py
```

## Model

For a fixed witness bucket with Poisson match intensity:

```text
lambda = 2^(witness_width - target_bits)
p_all = 1 - exp(-lambda)
p_class = 1 - exp(-lambda / 2^c)
class_loss = -log2(p_class / p_all)
```

`class_loss` tends toward `c` bits when matches are rare and toward `0` bits
when the bucket contains many neutral matching seeds. The cost is therefore not
always exactly one bit. It is the conditional hit-probability loss after the
extra witness width has already been paid.

## Result

Focused run:

```text
python model_analysis/birth_channel_research/H101-neutral_parity_discount.py --eval-trials 8 --train-trials 12 --iterations 2
```

Best discounted parity row:

```text
slack=1
net=-0.027835 bits/atom
class_loss=0.830905 bits/record
base_margin=-1.449341 bits/record
```

Cheapest parity class row:

```text
slack=-12
class_loss=0.260736 bits/record
base_margin=-5.346307 bits/record
net=-0.057494 bits/atom
```

The mechanism is real: parity/readiness can be cheaper than `1` bit/record
when the selected bucket has neutral multiplicity. The problem is that making
the bucket wide enough to get the discount spends more witness budget than the
discount returns in the current H9 fixed-slack frontier.

## Verdict

Neutral multiplicity does not rescue the current parity-ready two-epoch lane.
It refines H100's target from:

```text
base margin > 1 bit/record
```

to:

```text
base margin > class_loss bits/record after the width/slack bill
```

In the tested frontier the best class loss is cheaper, but the base margin is
too negative. The next target is still a separate paid witness mechanism that
creates positive record margin before the readiness class is imposed, or a
collective witness language where the class constraint is amortized globally.
