# H114 - Frozen Delta Law Plus Two-Epoch Parity

Date: 2026-06-18

## Question

H113 found a paid near miss for partial refresh:

```text
fixedD + visible two-epoch parity ~= +0.023438 bits/atom
```

Can a public frozen delta law replace the crude fixed-delta width stream without
reintroducing a per-file histogram?

Runnable artifact:

```text
model_analysis/birth_channel_research/H114-frozen_delta_parity_refresh.py
```

## Mechanism

For each pass:

```text
current records use seed class t mod 2
old records use seed class (t-1) mod 2
old records must refresh or literalize before the class repeats
```

The decoder reads the visible seed class to choose open vs carry. No H2
ready/carry bitmap is charged. The class is paid by widening the visible global
witness by one bit:

```text
payload_width = class_local_width + 1
```

Payload boundaries are encoded by a frozen public law:

```text
P(delta | context), trained on independent uniform-law covers
```

No per-file width counts, chosen profile, final-board note, birth-pass tag, or
sparse hit map is stored.

## Result

Default held-out diagnostic:

```text
B4_K32_D128, slack=4, context=global
train delta    = -0.0115 bits/atom
held-out delta = -0.0209 bits/atom
q              = 0.555
records/atom   = 0.0417
avg arity      = 13.75
avg payload    = 46.67 bits
delta bits/rec = 2.837
```

Stronger focused repeat on the same row:

```text
train/eval = 32/64

seed 114114 -> -0.013144 bits/atom
seed 214114 -> -0.008421 bits/atom
seed 314114 -> -0.009607 bits/atom
seed 414114 -> -0.004403 bits/atom
```

## What Is Paid

Paid:

- one visible seed-class bit through widened witness supply;
- frozen public delta-code bits per selected record;
- arity bits using the custom extended-arity accounting;
- residual age entropy if the two-epoch invariant is not enforced.

Not charged because it is not present in this branch:

- H2 ready/carry bitmap;
- birth-pass ledger;
- per-file delta histogram;
- final-position/egg-carton note;
- checksum/referee selector.

## Caveats

This is not yet a finished Telomere file format.

- It is a custom extended-arity target, not exact current V1 arity 1..5.
- The layer must already be a parseable record layer; raw/literal bootstrap
  overhead still needs a format-level treatment.
- The two-epoch invariant is load-bearing. If old records may survive past one
  carry pass, parity aliases and the missing age entropy returns.
- A codec spec must prove sequential parse: current records advance by arity;
  carried old records advance as one record atom.
- The public delta law must be frozen profile data, not selected per file.

## Verdict

This is the first paid, parseable partial-refresh target in this run that
crosses the uniform toy kernel after the main hidden channels are priced.

It should be promoted to the next constructive spec target:

```text
B=4 bits, K=32, D=128
q ~= 0.55 refreshed atoms/pass
records/atom ~= 0.035-0.042
mode = visible two-epoch seed class + frozen public delta law
held-out gain ~= 0.004-0.013 bits/atom in 32/64 repeats
```

The next work is not another broad search. It is an exact codec/accounting
proof for the two-epoch forced-refresh invariant and literal/bootstrap layer.
