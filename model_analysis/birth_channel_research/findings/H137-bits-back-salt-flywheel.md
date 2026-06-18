# H137 - Bits-Back Salt Flywheel

## Question

Can bits-back posterior tape solve the salting problem by generating fresh dice
across passes while remaining stateless and settled in the final stream?

Mechanism:

```text
decode latent cover for pass p
recover posterior tape
use tape bits as salt/dice for pass p+1
settle final tape in the stream
```

## Ledger

Closed-loop net:

```text
net = -P * marginal_gap
      + P * salt_bits * (gamma - 1)
      - final_or_initial_tape_settlement
```

where `gamma` is the future value per salt bit. Under uniform best-of-search,
`gamma <= 1`; a salt bit has one bit of opportunity cost.

## Result

Balanced tape, `gamma=1`, is conserved:

```text
P=64, gap=0.000, tape=64, salt=64:
  net = 0.000

P=64, gap=0.250, tape=64, salt=64:
  net = -16.000
  slope = -0.250 bits/pass

P=4096, gap=0.250, tape=64, salt=64:
  net = -1024.000
  slope = -0.250 bits/pass
```

Unbalanced tape is worse because the final or initial tape state must be
settled:

```text
P=64, gap=0, tape=64, salt=8:
  final delta = 3584 bits
  settlement = 3584 bits
  net = -3584

P=64, gap=0, tape=8, salt=64:
  final delta = -3584 bits
  settlement = 3584 bits
  net = -3584
```

Positive slopes appear only when `gamma > 1`, which means a separate
source/fertility law:

```text
P=4096, gap=0.250, tape=64, salt=64, gamma=1.1:
  net = 25190.400
  slope = 6.150 bits/pass
```

If salt also has to pay the H105 witness gap plus a near-total exception
ledger, the required `gamma` is only slightly above one but still not supplied
by bits-back itself:

```text
P=4096, eps=0.001:
  required gamma = 1.007686944

P=4096, eps=0.01:
  required gamma = 1.010458541
```

## Interpretation

Bits-back can be the right implementation scaffold for stateless salting:
canonical reverse decode can recover tape, consume salts in public order, and
settle the final state. But the tape is conserved state. It does not create the
missing witness margin.

The only live path is:

```text
bits-back salt scaffold
+ real public fertility/source law with gamma > 1
```

Without that, the flywheel is either exactly conserved or negative after final
tape settlement.

## Artifact

`model_analysis/birth_channel_research/H137-bits_back_salt_flywheel.py`
