# H187 - Shared Macro-Witness / Batch Seed

## Conjecture

```text
One witness might carry several spans at once, amortizing witness overhead and
preserving useful exact-witness supply across recursive passes.
```

The strongest form is a macro record whose root deterministically expands into
an ordered cover of child spans/records.

## Kernel

`H187-shared_macro_witness.py`

The kernel compares:

- independent V1 records;
- public layer packing of independent ranks;
- one joint seed/rank whose width is the sum of child rank widths;
- one contiguous fixed-arity macro record.

For arbitrary uniform targets:

```text
coverage log2 = W_total - T_total
```

Header/tier sharing does not change that target-tuple supply.

## Result

Representative rows:

```text
m=4,T_i=16,W_i=8:  T=64, independent=64, packed=48, joint=42,
                   saveJ=22, coverage log2=-32
m=8,T_i=16,W_i=16: T=128, independent=200, packed=153, joint=140,
                   saveJ=60, coverage log2=0
m=16,T_i=32,W_i=16:T=512, independent=400, packed=297, joint=269,
                   saveJ=131, coverage log2=-256
```

Shared macro witnesses can save parse/tier overhead. They do not name more
target tuples than their rank bits.

## Bill

```text
W-bit macro rank names at most 2^W target tuples
T output bits require coverage fraction 2^(W-T)
```

If a macro appears to beat this, it is using a generated/source promise, an
unpriced residual, or an overfull witness inventory.

## Mutation

Keep macro witnesses as a valid overhead-amortization and generated-regime
geometry. They do not by themselves change the H177/H182 row-mass bound for
arbitrary roughly-uniform data.
