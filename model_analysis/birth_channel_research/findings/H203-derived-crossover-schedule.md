# H203 - Decoder-Derived Crossover Schedule

## Conjecture

```text
Make the recombination schedule deterministic from parent roots, digest tails,
path state, or another decoder-known value, so no crossover rank is stored.
```

This attacks H202's exact bill: the crossover rank.

## Kernel

`H203-derived_crossover_schedule.py`

For every ordered parent tuple, the decoder derives one breakpoint set and one
segment-parent path:

```text
(breakpoints, path) = H(parent_roots, public_params)
child = Recombine(parent_1, ..., parent_p, breakpoints, path)
```

Because the schedule is a function of the stored parent tuple, each tuple names
at most one child.

## Result

Exact tiny row:

```text
G=3,C=8,B=8,A=2,P=2,L=4,N=32

p=2,t=1:
  parent_tuple_bits = 6
  support = 61
  support_log2 = 5.930737
  paid_index_net = -0.069263
  native_fixed_net = -15.069263
  native_stored_net = -22.069263
  support_gap = 26.069263

p=4,t=3:
  parent_tuple_bits = 12
  support = 1744
  support_log2 = 10.768184
  paid_index_net = -1.231816
  native_fixed_net = -30.231816
  support_gap = 21.231816
```

The best exact derived-schedule row nearly fills the parent-tuple support, but
does not exceed it.

Large H198 bound:

```text
N=500000,G=16,A=5,P=6,L=15625

p=2,t=0..32:
  support_bound = 32
  support_gap = 499968
  native_fixed_net = -21
  native_stored_net = -29

p=4,t=0..32:
  support_bound = 64
  support_gap = 499936
  native_fixed_net = -41
  native_stored_net = -49
```

Increasing `t` changes the deterministic child shape, but it does not add
address rank because there is still one child per parent tuple.

## Bill

The removed crossover-rank bill reappears as lost support:

```text
support_bits <= p*G
```

If the encoder can choose among schedules, that choice is a selector and H202
applies. If the decoder chooses canonically, the schedule is free but contributes
no new rank.

## Mutation

Move from one deterministic child per parent tuple to a public multi-child
orbit with a decoder-derived accept/reject rule:

```text
for j in public orbit(parent_tuple):
    child_j = Recombine(parent_tuple, schedule_j)
choose first child_j satisfying visible invariant F(child_j)
```

The next theorem to test is whether the visible invariant creates useful
recurrent fertility, or only burns orbit candidates and returns to
`support_bits <= pG` unless an accepted-index/referee channel is paid.
