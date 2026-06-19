# H202 - Recombination / Crossover Selector Ledger

## Conjecture

```text
Biology-like recombination of generated H198 parent trees may create many more
reachable phenotypes than plain multi-root XOR while keeping stateless decode.
```

The tested record is:

```text
[mode][parent root records...][crossover rank]
```

Parent count and crossover count are fixed by the public mode in the generous
lower bound. Charging them as profile symbols would only worsen the result.

## Kernel

`H202-recombination_crossover_ledger.py`

Exact tiny rows enumerate H198 parent phenotypes, ordered parent roots,
breakpoint choices, and segment-parent paths. For `p` parents, `t` crossover
points, and `L=A^P` leaves, the ideal crossover-rank bill is:

```text
grammar_bits = log2 C(L-1,t) + log2(p) + t*log2(p-1)
```

For `p=2` this is:

```text
grammar_bits = 1 + log2 C(L-1,t)
```

The large H198 bound uses:

```text
support_bits <= p*G + grammar_bits
paid_index_net <= support_bits - (p*G + grammar_bits)
native_net <= support_bits - (mode + p*root_record_bits + grammar_bits)
```

## Result

Exact tiny row:

```text
G=3,C=8,B=8,A=2,P=2,L=4,N=32

p=2,t=1:
  grammar_bits = 2.584963
  selection_bits = 8.584963
  support = 176
  support_log2 = 7.459432
  paid_index_net = -1.125531
  native_net = -23.125531
  support_gap = 24.540568

p=4,t=3:
  grammar_bits = 6.754888
  selection_bits = 18.754888
  support = 4096
  support_log2 = 12.000000
  paid_index_net = -6.754888
  native_net = -42.754888
  support_gap = 20.000000
```

The exact support is below the selected parent/rank count because many parent
choices are unused, duplicated, or colliding in this tiny regime.

Large H198 generous bound:

```text
N=500000,G=16,A=5,P=6,L=15625,root_record_bits=26

p=2:
  t=1  grammar=14.931476  support_bound=46.931476  fixed_native_net=-21
  t=32 grammar=329.098145 support_bound=361.098145 fixed_native_net=-21

p=4:
  t=1  grammar=17.516439  support_bound=81.516439  fixed_native_net=-41
  t=32 grammar=380.816945 support_bound=444.816945 fixed_native_net=-41
```

Stored pass count worsens those rows by another 8 bits:

```text
p=2 stored_native_net=-29
p=4 stored_native_net=-49
```

Adding crossover points increases the reachable set, but the same crossover
rank is exactly the decoder bill. The native loss is independent of `t` in the
generous bound:

```text
native_fixed_net <= p*G - (1 + p*record_cost_for_payload_width(A,G))
```

For the H198 `G=16,A=5` row, that is `-21` bits at two parents and `-41` bits
at four parents.

## Bill

```text
parent root identity + breakpoint rank + segment-parent rank
```

If the crossover schedule is not stored or publicly fixed, the decoder does
not know which recombinant child was meant. If it is stored as an ideal
arithmetic rank, its support gain cancels its cost. Native H198 root records
then add the Lotus/root overhead.

## Mutation

Plain recombination is closed as an arbitrary-uniform residual mechanism. The
next biological mutation has to make the crossover schedule decoder-derived
from visible state, or move to an explicit source/reachable population where
parent choice and crossover law are part of the paid source model. In arbitrary
uniform mode, this result reduces to selected-root/rank conservation rather
than a new witness-supply source.
