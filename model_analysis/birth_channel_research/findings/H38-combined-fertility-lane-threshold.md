# H38 - Combined fertility-lane threshold

Date: 2026-06-17

## Question

What happens when the strongest adjacent pieces are combined?

```text
H18 neutral witness multiplicity
H28 public fertility class
H36 developmental/source-shaped value lift
H37 d-choice public lane routing
```

Does d-choice routing make the branch uniform-positive, or only lower the
source-shaped value-lift target?

## Combined formula

H18 gives a current witness deficit and same-cost neutral capacity:

```text
missing_bits_per_record = m
neutral_bits_per_record = c
gamma = future saved bits per neutral bit
```

A public lane with active fraction `r` and `d` public candidate cells has:

```text
lane_loss = -log2(1 - (1-r)^d)
```

If the neutral/developmental witness must also satisfy the public lane, the
crossing condition is:

```text
gamma > (m + lane_loss) / c
```

So d-choice reduces the added lane penalty, but it does not remove H18's
current deficit.

## H18 baseline

H18's best no-lane row is:

```text
slack=-8
missing_bits_per_record=4.565
neutral_bits_per_record=3.819
records_per_atom=0.010987
gamma_needed_no_lane=1.195
gain_at_gamma_1=-0.008196 bits/input atom
```

One-for-one neutral credit is still short.

## H18 plus public d-choice lane

For the best H18 row:

```text
r=0.10,d=1:  lane_loss=3.322, gamma_needed=2.065
r=0.10,d=8:  lane_loss=0.812, gamma_needed=1.408
r=0.10,d=16: lane_loss=0.296, gamma_needed=1.273
r=0.10,d=32: lane_loss=0.050, gamma_needed=1.209

r=0.25,d=8:  lane_loss=0.152, gamma_needed=1.235
r=0.25,d=16: lane_loss=0.015, gamma_needed=1.199

r=0.50,d=8:  lane_loss=0.006, gamma_needed=1.197
```

So d-choice helps substantially compared with a single lane, but the combined
neutral branch still needs `gamma > 1`.

At `gamma=1`, the best `r=0.10,d=16` row is still short:

```text
gain_at_gamma_1=-0.011444 bits/input atom
```

## Public fertility class alone

If the public class is used as a value/count separator without H18's current
neutral deficit, the required value lift per selected record is just:

```text
value_lift > lane_loss
```

H38 examples:

```text
r=0.10,d=1:  required_lift=3.322 bits/record
r=0.10,d=8:  required_lift=0.812 bits/record
r=0.10,d=16: required_lift=0.296 bits/record
r=0.10,d=32: required_lift=0.050 bits/record

r=0.25,d=8:  required_lift=0.152 bits/record
r=0.25,d=16: required_lift=0.015 bits/record
```

Uniform value lift remains zero, so uniform controls stay negative.

## Engineering target

The number of choices needed for a lane tax target:

```text
r=0.10, target 1.0 bits: d >= 7
r=0.10, target 0.5 bits: d >= 12
r=0.10, target 0.25 bits: d >= 18
r=0.10, target 0.10 bits: d >= 26
```

This makes d-choice routing a useful threshold reducer for a public fertility
lane.

## Verdict

H38 does not solve the original uniform/content-blind all-data goal.

- Uniform future value still has `gamma=0`.
- One-for-one bits-back/neutral value has `gamma=1`.
- H18 still needs `gamma > 1.195` with no lane.
- Adding a public lane requires extra value unless d-choice makes the lane tax
  tiny.

But H38 sharpens the constructive source-shaped target:

```text
public developmental/fertility source
+ fixed public dither/freshness
+ d-choice public lanes
+ measured value_lift > -log2(1-(1-r)^d)
+ random/uniform controls negative
```

The most reachable target is not "find 3.322 bits of lift for a 10% lane." With
`d=16`, it is only:

```text
value_lift > 0.296 bits per selected record
```

That is a realistic next toy-kernel threshold for a source-shaped Telomere-like
developmental model, while still honestly outside the uniform all-data claim.

## Artifact

`model_analysis/birth_channel_research/H38-combined_fertility_lane_threshold.py`
