# H87 - Native Soft-Law Cycle Ledger

Date: 2026-06-17

## Question

H86 found high future-value ROI for soft output laws. Does that imply
repeatable stateless compression, or does the cost of making a layer fertile
come back as a capacity bill?

Runnable artifact:

```text
model_analysis/birth_channel_research/H87-native_soft_cycle_ledger.py
```

## Accounting

For a visible law `P` over the exact H80 domain:

```text
delta = D(P || U) = n - H(P)
lift  = E_P[V] - E_U[V]
```

If a fixed native grammar can keep the layer `P`-shaped, the optimistic
source-shaped cycle margin against a witness miss `m` is:

```text
source_cycle_margin = lift - m
```

If the starting source is arbitrary uniform data, making visible output
`P`-shaped costs capacity:

```text
startup_shape_bill = n * (n / H(P) - 1)
startup_margin = lift - m - startup_shape_bill
```

## Key Rows

```text
law           delta      lift      shape_bill  cycle H58  startup H58
d=0.005870   0.005870   0.235064  0.005873    0.005869  -0.000004
d=0.030000   0.030000   0.527059  0.030075    0.297864   0.267788
d=0.216226   0.216226   1.374892  0.220194    1.145697   0.925503
d=1.158938   1.158938   2.962770  1.282832    2.733575   1.450744
Q/native      1.365022   3.179817  1.540226    2.950622   1.410397
```

Soft-law threshold rows:

```text
target        theta    delta     shape     lift      startup
H84 one-shot  0.04616  0.004962  0.004964  0.216226 -0.004964
H58 nearest   0.04898  0.005579  0.005581  0.229195 -0.005581
H7 record     0.32601  0.210348  0.214101  1.357000 -0.214101
```

## Reading

The tiny threshold rows are not enough once the uniform-to-soft-law capacity
bill is charged. Stronger soft laws can keep a positive source-shaped margin in
this ledger, but that still does not prove all-data compression. It assumes
that the H80 future-value score becomes actual paid second-pass Telomere witness
savings.

The useful separation is:

```text
source-shaped cycle: maybe positive if native grammar preserves P
roughly-all uniform start: still needs a real witness-saving theorem, not only
                         score lift
```

## Verdict

H87 keeps the soft-law route alive as a source/native-language target, but it
does not solve the roughly-all-data requirement.

The next kernel should test finite parse overhead for a frozen public grammar,
then separately test whether measured value lift becomes real witness savings.
