# H82 - Syntax Support Capacity

Date: 2026-06-17

## Question

After H81, the remaining target is a native compact syntax whose visible output
is already fertile. Does the simplest version work?

```text
Only allow visible record strings in public fertile class F.
```

Runnable artifact:

```text
model_analysis/birth_channel_research/H82-syntax_support_capacity.py
```

## Ledger

If a public class has uniform mass `f=U(F)` and source mass `q=Q(F)`:

```text
support tax               = -log2(f)
class-membership dividend =  log2(q/f)
forced-subset net         =  log2(q)
```

Because `q <= 1`, membership alone cannot be positive.

## Exact Rows

```text
class        f=U(F)   Q(F)    tax    dividend    net
top2.5       0.0249   0.2484  5.328    3.318   -2.009
top10        0.1001   0.5323  3.321    2.411   -0.910
top25        0.2500   0.7787  2.000    1.639   -0.361
F_positive   0.2551   0.7839  1.971    1.619   -0.351
top50        0.5000   0.9398  1.000    0.910   -0.090
bottom25     0.2500   0.0079  2.000   -4.978   -6.978
```

## Verdict

A native syntax cannot win merely by declaring fertile strings valid.

This does not rule out a graded record language whose actual code lengths and
visible syntax are jointly fertile. It rules out support membership as the
missing free channel.

The next valid native-syntax target must test a full public probability law over
record strings, not just a valid/invalid subset.
