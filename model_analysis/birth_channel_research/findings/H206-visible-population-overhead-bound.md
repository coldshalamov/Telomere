# H206 - Visible-Population Arbitrary-Uniform Overhead Bound

## Conjecture

```text
Maybe the H205 arbitrary-uniform miss can be tuned away by changing population
size, root width, or arity.
```

## Kernel

`H206-visible_population_overhead_bound.py`

For a visible population of `M` root records:

```text
support_bits <= M*G
paid_bits = 1 + M*record_cost_for_payload_width(A,G)
uniform_net_upper = M*G - paid_bits
```

The kernel sweeps exact current V1/J3D1 root-record costs.

## Result

Best arbitrary-uniform upper bound in the scanned current-format rows:

```text
M=1,A=2,G=1
record_bits = 7
paid_bits = 8
support_bits = 1
uniform_net_upper = -7
generated_out_bits = 2048
inside_generated_gain = 2040
```

The same `-7` bound appears for `A=1,G=1`, but that has no useful branching
growth.

Best high-growth H198/H205-style branch:

```text
M=1,A=5,G=1
record_bits = 8
paid_bits = 9
support_bits = 1
uniform_net_upper = -8
generated_out_bits = 500000
inside_generated_gain = 499991
```

The familiar `G=16,A=5` row is:

```text
M=1,A=5,G=16
record_bits = 26
uniform_net_upper = -11
inside_generated_gain = 499973
```

For larger visible populations the deficit scales by root overhead:

```text
uniform_net_upper = -1 - M*(record_bits-G)
```

## Bill

Every legal current V1/J3D1 root record has:

```text
record_cost_for_payload_width(A,G) > G
```

Therefore:

```text
uniform_net_upper < 0
```

for all visible-population generated laws in the current root-record language.

## Mutation

The visible-population family has a finite arbitrary-uniform miss of 7 bits in
the best scanned current-format row, or 8 bits for the nontrivial `A=5`
high-growth branch. Closing it requires a real source/reachable membership law
or a different root-record language whose paid self-description is not larger
than its support rank.
