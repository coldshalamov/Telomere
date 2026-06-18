# H152 - Superposition Gap Ledger

Date: 2026-06-18

## Question

Can the user's non-greedy/superposition idea beat greedy Telomere paths by
allowing a bloated intermediate layer, while still storing only one final
visible witness stream?

Runnable artifact:

```text
model_analysis/birth_channel_research/H152-superposition_gap_ledger.py
```

## Model

This is an exact tiny `B=1` model using H96's paid V1/J3D1 record family.
For every bottom word `x`, it enumerates all visible intermediate record
streams `c` within a slack cap:

```text
c decodes to x
len(c) <= len(x) + slack
```

It then compares:

```text
greedy-visible:      choose the shortest current c
non-greedy-visible:  choose the c whose cheapest final stream y is shortest
cloud/oracle:        use the summed future description mass over all c
```

Only the final visible stream `y` is stored in the honest selected case. The
cloud/oracle gap is:

```text
log2(total future mass over allowed c / best explicit final-stream weight)
```

That gap is the rank/arithmetic channel required to exploit the whole
superposition instead of one parseable witness.

## Results

Baseline row matching H150's tiny paid family:

```text
N=4,K=4,D=7,slack=12:
  first coverage = 1.000000
  selected two-pass coverage = 1.000000
  mean greedy final = 31.562500 bits
  mean best final = 31.187500 bits
  visible non-greedy lift = 0.375000 bits
  non-greedy intermediate fraction = 0.062500
  selected gain = -27.187500 bits/word
  cloud gain = -20.574862 bits/word
  cloud gap = 6.612638 bits
```

Higher tiny arity/depth:

```text
N=5,K=5,D=8,slack=10:
  selected coverage = 1.000000
  mean best final = 30.093750 bits
  visible lift = 0.375000 bits
  selected gain = -25.093750 bits/word
  cloud gap = 6.029432 bits
```

Larger tiny word:

```text
N=6,K=5,D=7,slack=18:
  selected coverage = 1.000000
  mean greedy final = 43.484375 bits
  mean best final = 41.593750 bits
  visible lift = 1.890625 bits
  non-greedy intermediate fraction = 0.406250
  selected gain = -35.593750 bits/word
  cloud gain = -27.724882 bits/word
  cloud gap = 7.868868 bits
```

Adding many more intermediate candidates mostly increases the cloud/rank gap,
not the explicit selected-stream result. In `N=4,K=4,D=7`, increasing slack
from `12` to `20` raises average candidates from `8.687500` to `767.000000`,
but the best explicit final stream stays at `31.187500` bits while the cloud
gap rises from `6.612638` to `16.978981` bits.

## Reading

The user's objection is valid: greedy immediate shrinking wastes real option
value. H152 measures that value directly, and the best small row found here
gets almost two bits of visible improvement by choosing a worse-looking
intermediate.

That is still not enough in this paid family. The explicit final stream remains
much larger than the original word, and the larger superposition/cloud gain is
not available to a stateless decoder unless the codec pays for a rank,
arithmetic distribution, or public source law. Without that, the decoder sees
one final stream, not the cloud.

## Verdict

Non-greedy recursive search remains a real research direction, but H152 turns
it into a sharper target:

```text
find a visible recurrent grammar where the non-greedy selected-stream lift
scales faster than the explicit final witness cost, not merely where the
unselected cloud mass grows.
```

The current paid V1/J3D1 tiny family does not cross. Its useful signal is that
non-greedy path choice is measurable and sometimes substantial; its failure is
that most apparent superposition advantage is still hidden rank/arithmetic
capacity.
