# H190 - Whole-Layer Minimum-Description Ledger

## Conjecture

```text
A canonical minimum over all witness widths for a whole layer might compress
uniform targets by using the shortest available witness and raw fallback.
```

This is the broad version of whole-layer macro witnesses, canonical
minimum-cover selection, collision coalescence, and width/rank lookahead.

## Kernel

`H190-whole_layer_min_description.py`

The kernel enumerates every `N`-bit output for small `N`. For every exact
V1/J3D1 payload width up to `Wmax`, each canonical seed witness maps
deterministically to one output. The encoder chooses the shortest witness if
available; otherwise it uses raw fallback.

Two modes are reported:

```text
oracle_file_choice: raw N bits versus bare witness record
paid_mode:          one raw/witness parse bit plus exact V1/J3D1 witness costs
```

The oracle is intentionally labeled unparseable: it omits the channel that tells
the decoder whether raw or witness syntax follows.

## Result

Representative rows:

```text
N=8, Wmax=16:  oracle avg=7.996094, paid avg=8.996094,
               oracle gain=0.003906, paid gain=-0.996094
N=12,Wmax=16:  oracle avg=11.988281, paid avg=12.988281,
               oracle gain=0.011719, paid gain=-0.988281
N=16,Wmax=16:  oracle avg=15.991653, paid avg=16.991653,
               oracle gain=0.008347, paid gain=-0.991653
```

Exact round trips passed for sampled raw and witness outputs.

## Bill

The apparent oracle gain is the missing parse/fallback bit:

```text
decoder must know raw versus witness syntax
```

Once that one bit is charged, the uniform average stays above the raw `N`-bit
layer. Additional witness widths do not help after their exact V1/J3D1 cost is
no longer shorter than raw.

## Mutation

Close whole-layer canonical-minimum selection as an arbitrary-uniform row-mass
escape. Keep it as a useful diagnostic: any future whole-layer macro result must
beat this paid source-code ledger, not only the unparseable oracle.
