# H89 - Actual Witness Savings

Date: 2026-06-17

## Question

H86-H88 showed that soft laws can score well under:

```text
V(x) = log2(Q(x) / U(x))
```

and that a frozen public type-class grammar can realize those laws at large
block sizes. Does that value-score lift become actual paid Telomere selected
record savings?

Runnable artifact:

```text
model_analysis/birth_channel_research/H89-actual_witness_savings.py
```

## Model

Use the exact H80/H74 finite domain:

```text
B=1, N=12, K=6, D=8, domain=4096
```

For each word, compute the actual best cover cost from the H74 max-product DP:

```text
best_cost(x) = -log2(max_description_weight(x))
paid_saving(x) = raw_bits - best_cost(x)
```

A source-shaped cycle with an ideal soft distribution matcher would need:

```text
E_P[paid_saving] - D(P || U) > 0
```

A finite frozen type-class matcher needs:

```text
E_Phat[paid_saving] - finite_bill > 0
```

## Domain Facts

```text
total-description Kraft Z: 6.769121872788e-01
best-description Kraft Z:  2.216061336221e-01
E_U paid_saving:          -5.022461
E_Q paid_saving:          -1.005994
positive-saving fraction:  0.029541
best paid_saving:          4.000000
worst paid_saving:        -21.000000
```

So `Q` strongly improves the source, but the actual selected-record cost is
still expanding on average.

## Result

Ideal score-tilted laws:

```text
law       delta      scoreLift  actual_saving  cycle
th=0.90   1.158938   2.962770      -1.272704  -2.431642
th=1.00   1.365022   3.179817      -1.005994  -2.371016
th=1.20   1.801482   3.577292      -0.511460  -2.312943
```

Finite frozen type-class laws:

```text
theta  m      bill      scoreLift  actual_saving  cycle
0.90   32768  1.444977   2.979168      -1.244812  -2.689789
1.00   32768  1.637543   3.195070      -0.984406  -2.621948
1.05   32768  1.734528   3.295267      -0.860565  -2.595093
```

Best scanned rows:

```text
best score-law:
theta=1.34, m=32768, bill=2.349213,
actual_saving=-0.181427, cycle=-2.530640

best oracle-saving law:
theta=1.04, m=32768, bill=2.341797,
actual_saving=-0.055359, cycle=-2.397156
```

Shuffled savings at the best score-law row:

```text
avg_cycle=-7.384625, max_cycle=-6.853363
```

The score is genuinely aligned with actual savings, because the shuffled
control is far worse. But the alignment is not strong enough to cross.

## Reading

H89 falsifies the current soft-`Q` value proxy as a complete mechanism in this
exact toy domain. H88's positive `eta` was a future-value score margin, not
verified compression.

The useful lesson is precise:

```text
soft native grammar: parseable and paid
Q-score fertility: real but insufficient
actual witness-cost fertility: still missing by about 2.4 bits/word
```

## Verdict

The next target should not be another `log2(Q/U)` score audit. It should search
for a native/public law whose value function is actual witness-cost reduction,
or a mechanism that reduces exact witness costs by roughly the measured
`2.4` bits/word gap in this toy domain without hiding a selector/profile.
