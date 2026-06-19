# H204 - Public Recombination Orbit With Visible Selection

## Conjecture

```text
A public orbit of recombination schedules plus a decoder-visible accept/reject
law might behave like biological selection and create useful recurrent support
without storing a crossover rank.
```

## Kernel

`H204-public_orbit_selection.py`

For each parent tuple, the decoder derives an orbit of schedules:

```text
candidate_j = Recombine(parent_tuple, schedule_j)
accept_j = F(candidate_j)
```

The kernel prices two modes:

```text
canonical = first accepted candidate, no index
indexed   = chosen accepted candidate, accepted index/rank paid
```

The visible invariant in the default row is a simple prefix-zero class.

## Result

Exact tiny row:

```text
G=3,B=8,A=2,P=2,p=2,t=1

S=1,z=0:
  canonical_log2 = 5.930737
  canonical_paid_net = -0.069263
  native_canonical_net = -15.069263

S=16,z=1:
  accepted_choices = 523
  tuples_with_accept = 48
  canonical_log2 = 5.459432
  canonical_paid_net = -0.540568
  indexed_log2 = 6.459432
  indexed_selector_log2 = 9.030667
  indexed_paid_net = -2.571236
```

Large H198 bound:

```text
N=500000,G=16,A=5,P=6,p=2

canonical S=256,z=1:
  canonical_support_bound = 32
  native_canonical_net = -21

indexed S=256,z=1:
  indexed_support_bound = 39
  native_index_net = -22
```

For four parents:

```text
canonical support_bound <= 64
native_canonical_net = -41
```

The orbit can improve the chance that a parent tuple has an accepted child, but
canonical selection still emits at most one child per tuple. Indexed selection
uses more of the orbit only by paying the index/rank.

## Bill

```text
canonical selection: lost support / class thinning
indexed selection: accepted-index entropy
```

The visible invariant does not create new address rank. It either filters the
parent tuples or introduces a selected-index channel.

## Mutation

Move to an inherited visible population law. Instead of using recombination to
cover arbitrary data, store a visible final population of seed records and let
decode deterministically unfold it through public parent/crossover/child laws.
That should be a strong generated/reachable positive control while preserving
the arbitrary-uniform membership bill.
