# H47 - frozen public residual law

Date: 2026-06-17

## Question

Can the remaining high-arity Total-Cover miss be closed by a richer public
selected-extreme residual law?

H11 used a low-dimensional effective-choice law:

```text
width ~= min of m_eff public first-hit draws
```

H47 centers each width on that public selected-extreme mode and then codes the
lattice residual with a small public table trained on independent uniform-law
covers and frozen before held-out evaluation. The stream is still:

```text
[arity][seed witness]
```

There are no carried records, no birth/open tags, no sparse hit maps, and no
final-position notes.

## Calibration run

Default bounded run:

```text
B=4, K=128, D=512
atoms=128
train trials=8
eval trials=4 per held-out seed
eval seeds=3701,4801
rank code=fixed
```

Train-selected row:

```text
law = m1/arity_bucket
coverage = 1.000
train gain/atom = -0.038435
eval gain/atom = -0.089252
missing bits/record = 7.030
records/atom = 0.012695
avg arity = 78.77
avg width = 312.62
rank bits/record = 312.615
arity bits/record = 2.717
residual bits/record = 6.775
```

All tested laws were negative. The best held-out diagnostic row was the same
as the train-selected row:

```text
m1/arity_bucket: -0.089252 bits/input atom
```

## Reading

This does not close the H7/H9 gap. The target from H46 was only about:

```text
1.36 bits/selected record
```

but this residual-table calibration increases the paid miss to:

```text
7.030 bits/selected record
```

The reason is the same accounting shape that H44 warned about: a richer public
law must still normalize its support. In this small held-out run the table pays
more residual/support entropy than it recovers from the selected-extreme shape.

The result is not a theorem against every residual law. It is a directional
negative result against the most direct "public lattice-Gumbel residual table"
follow-up. Any stronger version has to show a held-out gain over H7/H9, not
just a lower apparent selected width on the training covers.

## Verdict

Frozen residual tables are not the missing piece in this form. They are
parseable and stateless, but they push the current nearest miss away from zero.

The next systematic target should not be "add more table shape" unless it
also reduces support entropy. The live axes remain:

- reduce the paid witness gap without table overfit;
- find a true source/fertility value lift with uniform controls negative;
- use public position/lane machinery for decode geometry only after its supply
  tax is paid;
- keep normalized whole-cover `Q` as the accounting check for any hidden-cover
  or duplicate-cover idea.

## Artifact

`model_analysis/birth_channel_research/H47-public_residual_law.py`
