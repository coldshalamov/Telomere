# H84 - Graded Native Law

Date: 2026-06-17

## Question

After H81-H83, the remaining target is a graded native record probability law.
Can a visible law between uniform `U` and the H80 fertile source `Q` both save
bits and preserve fertility?

Runnable artifact:

```text
model_analysis/birth_channel_research/H84-graded_native_law.py
```

## Model

Define a tilted visible law:

```text
R_lambda(x) proportional to U(x) * 2^(lambda * log2(Q(x)/U(x)))
```

`lambda=0` is uniform. `lambda=1` is `Q`.

For a source law `P`, coding under law `C` and distribution-matching into
visible law `R` costs:

```text
visible_bits = raw_bits * (H(P) + D(P || C)) / H(R)
```

H84 reports:

- one-shot `Q -> R_lambda`;
- recursive invariant `R_lambda -> R_lambda`;
- mismatched `R_lambda -> Q`.

## Result

```text
lambda   H(R)   R(top25)   Q->R save   R->R save   R->Q save   H7?
0.00    12.000   0.2500      0.000       0.000      -1.815      no
0.50    11.555   0.5395      0.650       0.000      -0.345      no
0.80    11.038   0.6948      0.390       0.000      -0.050      no
0.90    10.841   0.7389      0.216       0.000      -0.012      yes
1.00    10.635   0.7787      0.000       0.000       0.000      yes
```

Best one-shot fertile row:

```text
lambda = 0.90
Q -> R saving = 0.216226 bits
R(top25) = 0.738867
invariant R -> R saving = 0
```

## Reading

The tilted law gives a real one-shot tradeoff: `Q` can be encoded into a
higher-entropy visible law `R` while retaining enough high-`Q` class membership.

But after that pass, the next input law is `R`, not `Q`. The invariant
`R -> R` case has zero saving because an `R`-distributed visible stream has
exactly `H(R)` bits of information per `R`-shaped output symbol.

Encoding `R` under `Q` is expanding unless `R=Q`.

## Verdict

Graded `Q`-family native laws can give transitional compression, but not
repeatable recursive compression by themselves.

The next target is sharper:

```text
Find a high-entropy fertile law, where fertility is not merely the entropy
deficit of Q.
```

This is the value/count separation problem in a cleaner form.
