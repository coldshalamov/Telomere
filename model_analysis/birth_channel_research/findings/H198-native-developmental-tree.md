# H198 - Telomere-Native Developmental Seed Tree

## Conjecture

```text
H183's generated/reachable positive control can be made Telomere-native:
one stored root record recursively unfolds into a tree of seed-bearing records
whose leaves emit phenotype bits.  Inside that generated class, exact-witness
supply is maintained across arbitrary passes without salting metadata.
```

This is a constructive generated-regime target, not an arbitrary-content claim.

## Kernel

`H198-native_developmental_tree.py`

Public parameters:

```text
G = root witness payload width
C = internal child seed width
B = leaf atom bits
A = fixed branch arity, 1..5 under current V1
P = recursive passes / tree depth
```

Wire model:

```text
[mode][optional Lotus(P)][root record]
root record = [arity=A][root witness]
```

Every internal node is a V1/J3D1 seed record. Child seeds are derived by:

```text
child_seed = H(parent_seed, depth, slot) truncated to C bits
```

Leaves emit phenotype atoms by:

```text
leaf_bits = H(leaf_seed, path) truncated to B bits
```

All salts are decoder-derived from parent seed, depth, and path. There are no
birth-pass maps, open/carry maps, hit maps, final-position maps, or hidden lane
selectors.

## Result

The strongest sampled generated row in the bounded sweep:

```text
G=16, C=8, B=32, A=5, P=6
out_bits = 500000
paid_bits = 35
root_record_bits = 26
internal_record_bits = 17
inside_generated_gain = 499965
reachable_tax_upper = 499984
optimistic_uniform_net = -19
min_per_pass_step_gain = 59
all_passes_shrink = True
roundtrip_ok = True
```

With `P` fixed by the public preset instead of stored in the header:

```text
G=16, C=8, B=32, A=5, P=6, fixed_pass_count
out_bits = 500000
paid_bits = 27
inside_generated_gain = 499973
reachable_tax_upper = 499984
optimistic_uniform_net = -11
min_per_pass_step_gain = 59
all_passes_shrink = True
roundtrip_ok = True
```

Exact small support check:

```text
G=8, C=8, B=16, A=3, P=2
out_bits = 144
paid_bits = 25
inside_generated_gain = 119
unique phenotypes = 256/256
observed_uniform_net = -17.000000
all_passes_shrink = True

G=8, C=8, B=16, A=2, P=2
out_bits = 64
paid_bits = 24
inside_generated_gain = 40
unique phenotypes = 254/256
observed_uniform_net = -16.011315
all_passes_shrink = True
```

The second row shows why observed support matters: collisions make the reachable
class smaller than the optimistic `2^G` bound and therefore make arbitrary
uniform use slightly worse.

## Bill

Inside the generated class:

```text
gain_inside = out_bits - paid_bits
```

For arbitrary uniform data, reachable support is at most `2^G` phenotypes:

```text
tax_reachable >= out_bits - G
uniform_net <= gain_inside - (out_bits - G)
            = G - paid_bits
```

Observed collisions only reduce support further:

```text
observed_uniform_net = gain_inside - (out_bits - log2(unique_phenotypes))
```

## Mutation

H198 is the cleanest stateless recursive positive control so far:

```text
lossless
deterministic
stateless decode
fresh path-derived salts
all passes shrink inside the reachable class
exact current V1/J3D1 root and internal record costs
```

It still does not solve roughly-all-data compression. The arbitrary-data bill is
now sharply isolated as reachable-set membership, not as a decode-order or
salting problem.

The next useful mutation is to test whether any hybrid can attach arbitrary
data to this generated tree with a residual smaller than the membership tax. If
the residual is exact rank/preimage information, it should cancel; the kernel
should measure that cancellation rather than assume it.
