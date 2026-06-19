# H180 - Cocycle Canonical Placement

## Conjecture

Position/cocycle state can make decode order stateless and path-independent, but
it cannot create new exact-witness supply under the uniform hash law. It is
decode geometry unless a row introduces a paid source law, selector, or
overfull grammar.

## Model

`H180-cocycle_canonical_placement.py` samples total-cover interval support with
five modes:

- `baseline`: H177 cover support.
- `observed_coord`: accepted witnesses emit random coordinate deltas; the
  decoder observes the state after expansion.
- `endpoint`: accepted deltas must allow final public coordinate zero.
- `edge_zero`: every edge is conditioned to have zero coordinate delta.
- `paid_routes`: the encoder can choose among `d` route/salt slots and pays
  `log2(d)` bits.

It also runs a diamond confluence check:

```text
public potential: always zero holonomy
random edge labels: zero holonomy with probability about 2^-g
```

## Results

Representative fixed-arity `K=8,N=128` rows:

| mode | slack | g | d | support | paid gain/record | reading |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| baseline | -1 | 0 | 1 | 0.676 | -1.000 | bloat buys support |
| observed_coord | -1 | 4 | 1 | 0.668 | -1.000 | same supply as baseline |
| endpoint | -1 | 4 | 1 | 0.691 | -1.000 | endpoint filter gives no supply gain |
| edge_zero | -1 | 4 | 1 | 0.000 | -5.000 | conditioning 4 bits kills support |
| paid_routes | 0 | 4 | 4 | 0.969 | -2.000 | support repaired by a paid selector |
| paid_routes | 1 | 4 | 4 | 0.544 | -1.000 | strict saving erased by route bill |

High-arity fixed `K=128,N=128` rows behave the same:

| mode | slack | g | d | support | paid gain/record | reading |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| baseline | -1 | 0 | 1 | 0.082 | -1.000 | sparse despite bloat |
| observed_coord | -1 | 4 | 1 | 0.092 | -1.000 | no supply lift |
| endpoint | -1 | 4 | 1 | 0.010 | -1.000 | final coordinate filter hurts |
| edge_zero | -1 | 4 | 1 | 0.002 | -5.000 | coordinate conditioning costs supply |
| paid_routes | -1 | 0 | 4 | 0.984 | -3.000 | support bought with route bits |
| paid_routes | 1 | 0 | 4 | 0.084 | -1.000 | route bill removes strict saving |

Diamond check:

| g | public potential ok | random zero holonomy | expected |
| ---: | ---: | ---: | ---: |
| 0 | 1.000000 | 1.000000 | 1.000000 |
| 4 | 1.000000 | 0.067000 | 0.062500 |

## Bill

For public placement acceptance `alpha(a) <= 1`:

```text
E_out <= sum_a alpha(a) * 2^-(ell(a)+s)
      <= 2^-s * sum_a 2^-ell(a)
      <= 2^-s
```

Observed state is free but does not change `alpha` above `1`. Conditioning
coordinate bits multiplies supply by `2^-g`. Encoder-selected routes multiply
gross support by `d` but cost `log2(d)` bits, restoring the H177 trade.

## Result

H180 solves a real decoder problem: public zero-holonomy coordinates can make
out-of-order decode path-independent. It does not solve the compression problem.
Every positive-looking support repair is paid as bloat, route bits, coordinate
filtering, final-board entropy, or source restriction.

## Mutation

Do not keep searching this family for supply. Use cocycle coordinates as a
supporting decode scaffold if a separate mechanism later supplies positive
paid drift. The remaining arbitrary-content target must break H177 by a real
no-tax recurrent population law or another currently unknown supply source.
