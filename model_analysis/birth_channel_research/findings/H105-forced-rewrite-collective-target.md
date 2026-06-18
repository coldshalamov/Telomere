# H105 - Forced-Rewrite Collective Target

Date: 2026-06-18

## Question

H102/H103 found the cleanest stateless-readiness shape:

```text
public two-epoch lane + class-local seed rank
```

That removes the visible seed-parity tax, but only if the forced-rewrite witness
family has positive base margin. How much honest collective witness margin is
still missing after that correction?

Runnable artifact:

```text
model_analysis/birth_channel_research/H105-forced_rewrite_collective_target.py
```

## Model

Exact H74 tiny domain:

```text
B=1, N=12
```

Rows reuse the H94 witness families:

```text
h92_lower:
  optimistic lower bound; not paid

custom_rank:
  normalized rank code

custom_record:
  normalized arity+rank record code

paid_lotus:
  paid J3D1-style width accounting
```

Ledgers:

```text
public:
  public lane supplies epoch/readiness; local rank has no parity tax

visible+1:
  seed witness carries readiness; add 1 bit/record

eps001:
  T=64, eps=0.001 near-total exception ledger added
```

## Result

```text
mode            K   D   log2 total   public    visible+1  eps001
h92_lower       8  12     1.001339   0.000000  1.000000   0.000000
custom_rank     8  10    -2.188694   0.692022  1.692022   0.752763
custom_record   6  12    -1.781751   0.468557  1.468557   0.520646
paid_lotus     12  12    -5.301885   2.233401  3.233401   2.287744
```

The public-lane correction matters: for the best honest row, it drops the
needed margin from:

```text
1.468557 bits/record with visible parity
```

to:

```text
0.468557 bits/record with public lane local grammar
```

But the honest row still does not cross.

## Verdict

The clean target is now:

```text
q=1 forced rewrite
+ public two-epoch lanes
+ class-local seed ranks
+ collective witness family with paid log2Z_total > 0
```

The nearest honest toy miss is `custom_record K=6,D=12`, needing `0.468557`
bits/record of real witness-margin/Kraft boost. This is substantially better
than the visible-parity target, but still not a solved compressor.
