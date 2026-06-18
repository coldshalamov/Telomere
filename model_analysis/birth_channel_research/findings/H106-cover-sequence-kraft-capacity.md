# H106 - Cover-Sequence Kraft Capacity

Date: 2026-06-18

## Question

H105's best honest target still needs `0.468557` bits/record. Could that gap be
closed simply by reallocating public record Kraft mass across arities?

Runnable artifact:

```text
model_analysis/birth_channel_research/H106-cover_sequence_kraft_capacity.py
```

## Model

Let `W_a` be the total Kraft mass of all record symbols with arity `a`. A
whole cover of `N` atoms is a sequence of arities summing to `N`, so:

```text
F_0 = 1
F_n = sum_a W_a F_{n-a}
```

For a uniquely parseable public record grammar:

```text
sum_a W_a <= 1
```

By induction:

```text
F_n <= 1
```

So arity reweighting can at best make the fixed-length whole-cover grammar
complete (`log2Z=0`). It cannot make `log2Z>0`.

## Result

```text
N   K   equal log2F   best valid divisor   random max
12  6   -1.781751     0.000000             -0.492237
12  8   -2.188694     0.000000             -0.833908
24  6   -1.807942     0.000000             -0.473271
24 12   -2.697638     0.000000             -1.280669
64 16   -3.087871     0.000000             -2.513940
```

The H105 `custom_record K=6,D=12` row is exactly the equal-arity `K=6,N=12`
cover-sequence mass. The deficit is not a random-hash accident.

Positive mass appears only by violating Kraft:

```text
M=sum_a W_a   log2F_N   valid?
1.00          0.000000  yes
1.10          0.275007  no
1.25          0.643856  no
2.00          2.000000  no
```

## Verdict

The missing `0.468557` bits/record cannot be recovered by public arity-weight
optimization inside an ordinary uniquely parseable record stream. That can move
a negative row up to zero, but the forced-rewrite target needs positive base
margin.

The next source of margin must be something other than ordinary arity/rank
mass allocation:

```text
invalid/underpriced code
named non-uniform source law
paid visible invariant
or genuinely new syntax not equivalent to a record-sequence Kraft recurrence
```
