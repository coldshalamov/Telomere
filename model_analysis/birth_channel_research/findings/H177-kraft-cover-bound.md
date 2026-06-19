# H177 - Kraft Cover Bound

## Conjecture

The total-cover all-block-replacement branch has a prefix-code conservation
law: if every record saves `s` paid bits and the arity stream is public and
prefix-free, then the random interval cover is subcritical for every `s > 0`.

## Model

For arity code length `ell(a)`, a record saving `s` bits can expose at most:

```text
2^(target_bits - ell(a) - s)
```

witness candidates. Under the uniform hash law:

```text
P(edge at arity a) <= 2^-(ell(a) + s)
```

The expected outgoing cover degree is:

```text
E_out <= 2^-s * sum_a 2^-ell(a)
```

The arity Kraft sum is at most `1` for a prefix-free arity language. Therefore
strict paid savings imply `E_out < 1` unless another paid or decoder-derived
channel supplies extra witness mass.

## Executable Check

`H177-kraft_cover_bound.py` simulates the stripped interval DAG with exactly the
edge probabilities above.

V1 arity code, `N=128`, `2000` trials:

| slack s | Kraft | Eout | support | mean reachable |
| ---: | ---: | ---: | ---: | ---: |
| -2 | 0.875000 | 3.500000 | 1.000000 | 129.000000 |
| -1 | 0.875000 | 1.750000 | 0.266000 | 59.807500 |
| 0 | 0.875000 | 0.875000 | 0.000000 | 4.243000 |
| 1 | 0.875000 | 0.437500 | 0.000000 | 1.763000 |
| 2 | 0.875000 | 0.218750 | 0.000000 | 1.273000 |

Fixed arity sanity, `N=64`, `300` trials:

| K | slack s | Kraft | Eout | support |
| ---: | ---: | ---: | ---: | ---: |
| 8 | -1 | 1.000000 | 2.000000 | 0.706667 |
| 8 | 0 | 1.000000 | 1.000000 | 0.010000 |
| 8 | 1 | 1.000000 | 0.500000 | 0.000000 |
| 32 | -1 | 1.000000 | 2.000000 | 0.456667 |
| 32 | 0 | 1.000000 | 1.000000 | 0.080000 |
| 32 | 1 | 1.000000 | 0.500000 | 0.000000 |

## Result

This is the exact reason total-cover feels close but keeps missing:

- bloat (`s<0`) is supercritical but grows the stream;
- flat (`s=0`) is critical at best and V1 is below critical because its arity
  Kraft sum is `0.875`;
- strict savings (`s>0`) are subcritical.

Increasing `K` can make the bloat per input atom small by increasing selected
arity, but it cannot make strict paid savings supercritical under the uniform
hash law with a valid prefix arity code.

## Mutation

Future candidates must break one of the theorem's premises honestly:

- use a generated/reachable source regime and state the source restriction cost;
- create a public non-uniform witness law and pay its class tax;
- spend same-cost collision multiplicity through lookahead and show its option
  value exceeds the bloat that created it;
- use canonical placement/cocycle geometry only if route choice is public and
  exceptions are charged.
