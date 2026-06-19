# H211 - Honest Induced-Prior Conservation

## Conjecture

```text
A recursive all-data encoder can make the emitted stream non-uniform, but the
best decoder-known next-pass prior over that emitted stream can only recover
the entropy already paid by the emitted stream.
```

This is the concrete push-forward version of H196/H208: enumerate the actual
emitted record stream distribution rather than inventing a `P_beta` source.

## Kernel

`H211-honest_induced_prior_conservation.py`

For every tiny input:

```text
1. build public exact witnesses using current V1/J3D1 costs;
2. canonical encode with witness if shorter, otherwise raw;
3. verify decode;
4. measure P_emit over actual emitted tokens;
5. compare next-pass priors:
   actual_code, class_uniform, oracle_emit=P_emit.
```

## Result

Default:

```text
N=8,arity=1,Wmax=8
witnesses=509
cases=256
roundtrip=True
unique_emit=256
H_emit=8
mean_emit_bits=8.996094
first_pass_delta=0.996094
support_witness=1
raw=255

actual_code:   CE=8.001718, paidNet=-0.001718
class_uniform: CE=8.000000, paidNet=0
oracle_emit:   CE=8.000000, paidNet=0
```

Second row:

```text
N=10,arity=1,Wmax=9
roundtrip=True
H_emit=10
mean_emit_bits=10.993164
support_witness=5
raw=1019

actual_code:   CE=10.008579, paidNet=-0.008579
class_uniform: CE=10.000000, paidNet=0
oracle_emit:   CE=10.000000, paidNet=0
```

## Bill

The first pass creates almost one bit of apparent recoverable shape, but that
shape is exactly the first-pass expansion:

```text
source_tax = mean_emit_bits - H(P_emit)
paid_net   = H(P_emit) - CE(P_emit,Q)
           = -D(P_emit || Q) <= 0
```

The oracle next-pass prior ties.  It does not go positive.

## Mutation

Close self-induced source bias as an arbitrary-uniform engine unless a future
mechanism violates one premise honestly: external source law, generated
membership, bounded referee surplus, non-uniform expander, or a paid public
model whose actual `CE` beats its own source tax.
