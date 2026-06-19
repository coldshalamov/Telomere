# H183 - Generated / Reachable Recursive Codec

## Conjecture

```text
A bounded generated regime can have real negative paid length drift with
stateless recursive decode, but arbitrary-content use pays the reachable-set
membership tax.
```

This is the positive-control branch, not an arbitrary-content solution. It is
Telomere-compatible in the sense that a short witness/root names a deterministic
public expansion, and decode does not search.

## Kernel

`H183-generated_reachable_codec.py`

Wire model:

```text
Header: generated-regime mode
Record: [arity=1][root witness] with exact V1/J3D1 root cost
Optional header: Lotus(pass_count)
Decode: public BLAKE2b counter expander for P recursive passes
```

No carried records, sparse open/carry map, birth-pass map, hit map, final-board
map, or PCTB ledger is used.

## Result

Representative rows:

```text
G=8,  P=2, out=64:   paid=24, gain_inside=40,  tax=56,   uniform_net=-16
G=12, P=4, out=512:  paid=28, gain_inside=484, tax=500,  uniform_net=-16
G=12, P=6, out=2048: paid=29, gain_inside=2019,tax=2036, uniform_net=-17
G=16, P=6, out=4096: paid=34, gain_inside=4062,tax=4080, uniform_net=-18
```

All tested roots were unique and round-tripped:

```text
G=8:  256/256 unique
G=12: 4096/4096 unique
G=16: 65536/65536 unique
```

## Bill

Inside the generated class:

```text
gain_inside = phenotype_bits - paid_bits
```

For arbitrary uniform data:

```text
reachable_tax = phenotype_bits - root_bits
uniform_net = gain_inside - reachable_tax
```

The reachable-set tax cancels the root-vs-phenotype saving, leaving the exact
mode/root/pass overhead. This is why generated/DNA-like unfolding is real but
does not by itself solve arbitrary all-content recursion.

## Mutation

Keep generated regimes as honest source-shaped positives and positive controls.
The remaining arbitrary-content target must either find a real paid row-mass
boost beyond Kraft, or identify a natural source class whose membership is part
of the problem statement rather than hidden in the codec.
