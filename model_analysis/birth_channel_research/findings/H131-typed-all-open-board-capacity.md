# H131 - Typed All-Open Board Capacity

## Question

If the public board makes every slot type known in advance, can it solve both
stateless decode and positive compression?

Typed board invariant:

```text
every slot opens
arity/child count is public
width/target class is public
seed class and salt are public
placement coordinates are public
only witness payload remains in the stream
```

## Counting Model

Let the previous layer have `N` bits and the typed board carry `W` witness bits.
If the board saves `G = N - W` bits, then under the uniform hash law the expected
covered fraction is:

```text
p = 1 - exp(-2^(W-N)) = 1 - exp(-2^-G)
```

## Result

Positive gain loses roughly-all coverage.

```text
G=1 bit saved:
  coverage/pass = 0.393469

G=2 bits saved:
  coverage/pass = 0.221199

G=0 bits saved:
  coverage/pass = 0.632121
```

High per-pass coverage requires bloat:

```text
coverage/pass = 0.90:
  max gain = -1.203254 bits

coverage/pass = 0.99:
  max gain = -2.203254 bits

coverage/pass = 0.999999:
  max gain = -3.788217 bits
```

Over many passes the survival target is even harsher:

```text
final coverage 0.90 over 4096 passes:
  per-pass coverage = 0.999974278
  max gain = -3.401650 bits
```

## Interpretation

A typed all-open public board is an excellent stateless decode geometry, but it
is not by itself a compression source. If the witness stream is shorter than
raw, it cannot cover roughly all arbitrary layers. To cross, the recursive layer
distribution must become non-uniform/fertile under a public law, or the witness
family must provide honest Kraft mass beyond the fixed-board public codebook.

## Artifact

`model_analysis/birth_channel_research/H131-typed_all_open_board_capacity.py`
