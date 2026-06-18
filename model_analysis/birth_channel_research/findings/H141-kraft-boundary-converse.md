# H141 - Kraft Boundary Converse

Date: 2026-06-18

## Question

Can the decoder infer payload width or record boundary from the seed witness
itself, using residue classes, trailing patterns, parity/sign lanes, canonical
minimum seeds, or a self-delimiting seed language, and thereby recover the
local-width oracle from H110/H140?

Runnable artifact:

```text
model_analysis/birth_channel_research/H141-kraft_boundary_converse.py
```

## Model

Any seed-derived boundary rule that decodes without side information is a
prefix or uniquely decodable witness language. Its inventory obeys Kraft:

```text
sum_witness 2^(-len(witness)) <= 1
```

For a fixed record delta:

```text
record_delta = arity_bits + seed_width - arity * B
```

the best possible slack-legal option supply is achieved by spending all Kraft
mass at one public seed width and one best arity. That is a public fixed-width
witness lane, not the local-width oracle.

For a central atom:

```text
lambda(k) = k * 2^(seed_width - k*B)
q         = 1 - exp(-max_k lambda(k))
```

For power-of-two `K`, the best large-arity row is approximately:

```text
lambda = 2^record_delta
```

## Results

Representative exact rows:

```text
B=4,K=32,delta=-2:
  best arity = 32
  q = 0.221199
  H2/q = 3.446446 bits per rewritten atom
  partial+H2 = +0.748526 bits/atom
  fixed-slot literal fallback = +0.059188 bits/atom

B=4,K=32,delta=-1:
  q = 0.393469
  partial+H2 = +0.954706 bits/atom
  fixed-slot literal fallback = +0.044566 bits/atom

B=4,K=32,delta=0:
  q = 0.632121
  partial+H2 = +0.949030 bits/atom
  fixed-slot literal fallback = +0.034489 bits/atom

B=4,K=32,delta=2:
  q = 0.981684
  partial+H2 = +0.193231 bits/atom
  fixed-slot literal fallback = +0.063072 bits/atom
```

Best scanned rows:

```text
B4 K32:
  best partial+H2 delta = +0.125003 bits/atom
  best public fixed-slot delta = +0.034489 bits/atom
  first q>=0.90 requires delta=+2 bits/record

B4 K128:
  best partial+H2 delta = +0.031253 bits/atom
  best public fixed-slot delta = +0.008622 bits/atom
  first q>=0.90 requires delta=+2 bits/record
```

## Reading

Seed-derived width is not free width. If the decoder can infer the boundary
from the seed bits, those bits form a self-delimiting code and must obey Kraft.
The local-width oracle violates that by effectively giving every width a full
binary seed inventory.

The best Kraft-valid replacement for that oracle is a public fixed-width lane.
It can refresh, but:

```text
compressive records are too sparse,
flat records fail too often,
near-total freshness needs bloating records.
```

Partial selection pays `H2(q)` for the selected layout. Public fixed slots avoid
the bitmap but pay literal/type fallback for failed slots. Neither ledger goes
negative in the tested rows.

## Verdict

Residue/parity/trailing-pattern/self-delimiting seed-boundary tricks do not
recover the local-width oracle. They collapse to a fixed-width public lane or
an ordinary prefix width code. The remaining path must derive a near-total
public layout, find a collective width stream that beats this Kraft bound in a
different currency, or introduce a real non-uniform fertility law.
