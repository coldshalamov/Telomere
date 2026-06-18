# H28 - Public fertility-class target

Date: 2026-06-17

## Question

Can H26 be rescued by a decoder-visible public class that is both a state
signal and a high-fertility compression source?

Proposed shape:

```text
seed/position/lane -> public class
class -> salt + placement + expected future fertility
decoder derives class from seed/position/lane
encoder prefers matching seeds in high-fertility classes
```

The record remains:

```text
[arity][seed witness]
```

plus a fixed/root public profile if the class law is not built into the format.

## Uniform-hash control

If class `C` occupies fraction `f` of eligible seeds/positions, it costs:

```text
supply_loss = log2(1/f)
```

Under uniform hash over arbitrary targets, public class membership is
independent of target equality and selected value. Therefore:

```text
E[value | C] - E[value] = 0
```

Representative H28 rows:

```text
f=0.10      supply_loss=3.321928  uniform_extra_net=-3.321928
f=1/64      supply_loss=6.000000  uniform_extra_net=-6.000000
f=1/1024    supply_loss=10.000000 uniform_extra_net=-10.000000
```

So public classes do not maintain match rate for roughly all data under the
uniform hash law. They only spend supply unless the class predicts value.

## Breakthrough criterion

The exact criterion is:

```text
value_lift > log2(1/f)
```

where:

```text
value_lift = E[selected gain | public class C] - E[selected gain]
```

Equivalently, if:

```text
value_lift = gamma * log2(1/f)
```

then a class crosses only when:

```text
gamma > 1
```

H28 examples:

```text
f=0.10, gamma=1.0 -> extra_net = 0.000000
f=0.10, gamma=1.2 -> extra_net = 0.664386
f=1/64, gamma=1.2 -> extra_net = 1.200000
```

This is the same shape as the H18/H19 developmental/neutral ecology target.

## Neutral-choice version

Same-cost seed multiplicity can choose among neutral alternatives without
changing the current record length. If that neutral choice exposes `c` bits of
future steering capacity, it only beats conservation if each neutral bit saves
more than one future bit:

```text
future_value = gamma * c
net = (gamma - 1) * c
crosses only if gamma > 1
```

Uniform future value has `gamma=0`. A one-for-one channel has `gamma=1` and
merely breaks even before ordinary record costs.

## Verdict

This is the best biology-shaped target so far, but it is a premise shift, not a
free uniform-hash solution.

Valid next target:

```text
public developmental/fertility class
+ stateless class derivation from seed/position/lane
+ measured value_lift > log2(1/f)
+ random/uniform controls stay negative
```

Invalid shortcuts:

- choosing the class after seeing the file without storing the selector;
- using ordinary file structure/pattern tables and calling it Telomere;
- letting uniform controls cross, which would mean the entropy is hidden
  somewhere else.

If such a class crosses only for a public developmental source, that would be a
real Telomere-shaped analogue of DNA-like unfolding, but not the original
content-blind roughly-all-data claim.

## Artifact

`model_analysis/birth_channel_research/H28-public_fertility_class.py`
