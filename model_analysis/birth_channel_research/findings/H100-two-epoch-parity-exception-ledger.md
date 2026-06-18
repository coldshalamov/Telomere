# H100 - Two-Epoch Parity Exception Ledger

Date: 2026-06-18

## Question

H99 showed seed parity is a paid two-epoch discriminator, not a free many-pass
birth channel. Can that still be the missing stateless decode mechanism if the
codec enforces:

```text
records are current epoch or previous epoch, never older
```

Runnable artifact:

```text
model_analysis/birth_channel_research/H100-two_epoch_parity_exception_ledger.py
```

## Mechanism

Use two public seed classes:

```text
pass t births only seed class t mod 2
decoder opens class t mod 2
decoder carries class t-1 mod 2 exactly once
```

This is stateless only if every previous-epoch record is forced to open or be
refreshed on the next pass. If a record survives two passes, parity aliases and
the many-pass birth problem returns.

## Formula

Let:

```text
r = selected records per input atom
m = base paid margin before seed-class restriction, bits/record
q = fraction of output record slots born/refreshed this pass
c = seed-class bits
```

Two-epoch seed-class net:

```text
net_bits_per_atom = q * r * (m - c)
```

Positive condition:

```text
m > c
```

For even/odd parity, `c=1`.

## Result

Current rows do not survive the parity bill:

```text
target      q=1 parity net
H7 current  -0.020716 bits/atom
H9 current  -0.022079 bits/atom
H12 upper   -0.019183 bits/atom
```

A hypothetical real `+2` bits/record mechanism would survive:

```text
hyp +2.0 at H9 record density:
  q=1.00 -> +0.009765 bits/atom
  q=0.90 -> +0.008788 bits/atom
```

Residual age entropy confirms the lifetime invariant:

```text
live ages L, class bits c, residual H(age | age mod 2^c)
L=2,c=1    -> 0.000000 bits/record
L=64,c=1   -> 5.000000 bits/record
L=256,c=8  -> 0.000000 bits/record
```

So the decoder can forget absolute birth pass only when live lifetime is kept
to the class count. With two classes, that means two live epochs.

## Subagent Cross-Check

Two read-only subagents converged on the same shape:

```text
forced two-epoch public lane
+ position salt
+ mandatory old-cohort refresh
+ explicit rare exceptions
```

They identified the main hidden channel as enforcement: age-1 records must not
survive again unless rewritten into the current class or literalized. A prefix
boundary is not enough if the encoder selected arbitrary successful records and
sorted them forward; that hides the subset and costs `log2 C(N,R)`.

## Verdict

Two-epoch parity is a real stateless readiness layer, not a reward hack.

It does not supply compression by itself. It becomes useful only after another
mechanism creates more than `1` paid bit/record of base margin and the format
enforces maximum record lifetime `<= 1` pass. Under current H7/H9/H12 paid
frontiers, adding parity makes the miss worse.

This is now the sharpest constructive stateless-decode target:

```text
find or create m > 1 bits/record after exact Lotus/witness accounting,
then use two-epoch seed parity/public lanes to maintain stateless decode.
```
