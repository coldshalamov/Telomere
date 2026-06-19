# H194 - Finite-State Language Transform

## Conjecture

```text
A reversible public finite-state/self-delimiting language transform can force
all inputs into parseable syntax, preserve witness supply, and remove the
raw/witness mode problem without source restriction.
```

This tests the next target left by H193: keep support from collapsing after an
honest transform tax.

## Kernel

`H194-finite_state_language_transform.py`

For each language `L`, input width `N`, and exact V1/J3D1 witness frontier
`Wmax`, the kernel:

1. Finds the smallest `m >= N` with `|L_m| >= 2^N`.
2. Maps raw rank `0..2^N-1` into the first `2^N` accepted `m`-bit words.
3. Hashes exact seed witnesses to `m`-bit words.
4. Prices the induced distribution over the selected syntax set.

Two witness-accounting modes are reported:

```text
all_syntax:       every syntactic seed record up to Wmax consumes Kraft mass
semantic_reclaim: generous lower bound that reclaims rejected seed holes
```

The table reports:

```text
realGain = N - paid_mean
appGain  = m - paid_mean
```

`appGain` can be large because the transform expanded the layer. `realGain` is
the honest arbitrary-input test.

## Result

Representative rows:

```text
suffix0,N=8,m=9,W=16,semantic_reclaim:
  mean=8.001629, realGain=-0.001629, appGain=0.998371

marker4,N=12,m=15,W=16,semantic_reclaim:
  mean=12.002594, realGain=-0.002594, appGain=2.997406

no000,N=16,m=18,W=16,semantic_reclaim:
  mean=16.016377, realGain=-0.016377, appGain=1.983623
```

Nearest nonzero-support row in the default sweep:

```text
maxrun2,N=8,m=11,W=4,semantic_reclaim:
  mean=8.000721, realGain=-0.000721, appGain=2.999279
```

The apparent syntax gain is nearly three bits, but the original source had only
eight bits; after transform/rank accounting the row is still negative.

Bounded balanced/Dyck probes with larger transform overhead:

```text
dyck4,N=8,m=14,W=16,semantic_reclaim:
  mean=8.000311, realGain=-0.000311, appGain=5.999689

dyck4,N=12,m=20,W=16,semantic_reclaim:
  mean=12.000003, realGain=-0.000002878, appGain=7.999997

primdyck4,N=8,m=18,W=16,semantic_reclaim:
  mean=8.000000013, realGain=-0.000000013, appGain=10.000000
```

These are even closer to a tie because the selected witness mass is tiny after a
large surface expansion. They do not create maintained compression; they nearly
turn the witness mechanism off while making the syntax surface much longer.

## Bill

A reversible public transform chooses a selected set `S subset L_m` with
`|S|=2^N`. For arbitrary uniform ranks over `S`, the paid mean is:

```text
E_U[-log2 Q(X)] = N + D(U || Q) >= N
```

Language density changes where witnesses land, but it also costs:

```text
transform tax = m - N
syntax thinning = log2(|S| / 2^m) = N - m
```

Those are the same bill seen from opposite sides. Semantic rejection of seed
outputs is a generous lower bound unless the rejected code space is actually
reclaimed by a prefix/arithmetic grammar.

## Mutation

Finite-state syntax can make parse geometry clean and may be useful for a
declared generated/source-shaped regime. It did not produce arbitrary-uniform
negative drift. The next attack should either:

```text
1. add true generated/reachable fertility to the language and pay membership tax;
2. test neutral multiplicity inside the language for future value; or
3. search for a transform whose selected witness mass is unusually uniform,
   because only D(U||Q)->0 remains available for roughly-all data.
```
