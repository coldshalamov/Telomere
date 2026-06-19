# H199 - Generated Tree Plus Residual Attachment

## Conjecture

```text
Arbitrary data might be encoded as an H198 generated phenotype plus a small
residual. If the residual is cheaper than the reachable-set membership tax,
the generated tree could become a roughly-all-data recursive codec.
```

This tests the next target left by H198: attach arbitrary data to the generated
tree for less than preimage/rank/membership information.

## Kernel

`H199-generated_residual_attachment.py`

For tiny H198 codebooks, the kernel enumerates generated phenotypes and exact
Hamming-ball residual masks:

```text
target = generated_phenotype(root) XOR residual_mask
residual_mask in Ball(N, radius)
```

It reports:

```text
paid_root_bits = mode + optional pass count + record_cost_for_payload_width(A,G)
residual_bits  = log2 |Ball(N,r)|
covered        = |union_root (phenotype(root) XOR Ball(N,r))|
ideal_net      = log2(covered) - paid_root_bits - residual_bits
ceil_net       = log2(covered) - paid_root_bits - ceil(log2 |Ball|)
pair_bound     = log2(unique_roots) - paid_root_bits
```

The residual radius is public per row, so no sparse map or per-target hit bitmap
is charged.

## Result

Exact one-pass row:

```text
G=4,C=8,B=8,A=2,P=1,N=16,paid=17,unique=16/16

r=0:
  covered=16
  residual_log2=0
  ideal_net=-13.000000

r=4:
  residual_count=2517
  residual_log2=11.297490
  covered=30470
  coverage=0.464935
  ideal_net=-13.402388

r=8:
  residual_count=39203
  residual_log2=15.258676
  covered=65536
  coverage=1.000000
  ideal_net=-16.258676

r=16:
  residual_count=65536
  residual_log2=16.000000
  covered=65536
  coverage=1.000000
  ideal_net=-17.000000
```

Exact two-pass collision row:

```text
G=4,C=8,B=8,A=2,P=2,N=32,paid=12,unique=15/16,fixed_pass_count
r=4:
  residual_count=41449
  residual_log2=15.339050
  covered=621735
  coverage=0.000145
  ideal_net=-8.093109
```

The two-pass row shows the observed support bill: collisions reduce the
generated support to `15/16`, making the root-overhead bound
`log2(15)-12 = -8.093109`.

Large H198 bound for the best fixed-pass generated row:

```text
N=500000,G=16,paid=27
r=0:  netBound=-11
r=32: residual_log2=488.145592, unionLog=504.145592, netBound=-11
```

The radius can grow support, but after residual rank is paid, the bound remains
`G-paid`.

## Bill

For any root/residual attachment:

```text
support <= unique_roots * residual_count
ideal_net = log2(support) - paid_root_bits - log2(residual_count)
          <= log2(unique_roots) - paid_root_bits
```

Full coverage forces:

```text
log2(residual_count) >= N - log2(unique_roots)
```

which is exactly the reachable-set membership/preimage information.

## Mutation

H199 closes the direct arbitrary-residual attachment route. Generated trees are
still valuable as maintained recursive positive controls, but arbitrary residual
information cancels the membership tax unless a future mechanism can make the
residual itself recursively generative without adding an equivalent source
restriction.

