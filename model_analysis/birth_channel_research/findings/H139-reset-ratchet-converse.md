# H139 - Reset/Ratchet Converse

Date: 2026-06-18

## Question

Can a bounded reset, stop rule, or ratchet keep recursive shrinkage alive by
letting bad histories reset while good histories accumulate savings?

Runnable artifact:

```text
model_analysis/birth_channel_research/H139-reset_ratchet_converse.py
```

## Model

H139 applies the counting checks that any reset/ratchet claim must pass:

```text
claimed saving S bits -> prefix support at most 2^-S
claimed coverage c over P passes -> bad/reset probability must be O(1/P)
visible final state bits subtract from S
hidden best-of choices cancel when their selector is paid
variable length/reset paths are charged as path inventory
```

This is not a compression search. It is a short-output inventory ledger.

## Results

Representative rows:

```text
P64_s1_c90:
  S = 64 bits
  prefix coverage bound = 5.421e-20
  eps max for 90% survival = 0.0016449
  loser expansion needed for 90% coverage = 576 bits

P64_s1_c90_state64:
  visible state bits = 64
  charged saving = 0
  charged coverage bound = 1

P64_s1_c90_hidden2^32:
  apparent hidden bound = 2.328e-10
  paid hidden bound = 5.421e-20

P4096_s0.01_c90:
  S = 40.960 bits
  eps max for 90% survival = 2.57225e-05
  loser expansion needed = 368.640 bits
```

## Reading

Reset/ratchet schemes can be good bounded-loss engineering, but they do not
create maintained roughly-all compression under the uniform law.

If the final state is visible, it subtracts from the claimed saving. If the
encoder tries many hidden reset paths, the paid selector returns the coverage
bound to the raw prefix inventory. If a small reset probability is required for
many-pass survival, it must shrink like `O(1/P)`, which means another mechanism
already solved the reliability problem.

## Verdict

No positive stateless recursive compression source was found here. H139 closes
reset/stop/ratchet claims unless they bring a separately priced source of
fertility or a public invariant that makes resets vanish with pass count.
