# H78 - Master No-Go Audit

Date: 2026-06-17

## Theorem

For any stateless, lossless Telomere-admissible scheme on `n`-bit inputs, let
`L(x)` be the full visible output length, including every non-derivable header,
selector, final state, random/profile identity, and referee bit.

If the scheme is content-blind and compresses a fraction `c` of arbitrary
uniform inputs by total saving `S = P*s`:

```text
Pr_U[L(X) <= n - S] >= c
```

then:

```text
prefix / self-delimiting stream:  c <= 2^-S
EOF one-shot generous bound:      c <= 2^(1-S) - 2^-n
```

So:

```text
prefix: S <= -log2(c)
EOF:    S < 1 - log2(c)
```

At `c=0.90`:

```text
>=1 bit/pass:
  prefix/self-delimiting: K = 0
  EOF one-shot:           K = 1

>=2 bits/pass:
  prefix/self-delimiting: K = 0
  EOF one-shot:           K = 0
```

Runnable artifact:

```text
model_analysis/birth_channel_research/H78-master_no_go_audit.py
```

## Scope Covered

H78 includes the priced channels from H71-H76:

- public `Q` and latent whole-cover distributions;
- final boards / visible state;
- pass/birth/order/ready coordinates;
- randomized public codebooks;
- private encoder randomness;
- compute-as-best-of profiles;
- checksum/referee selection;
- rare blowups and bounded loser expansion.

All of them reduce to:

```text
visible output bits
public Q cross-entropy
short-output inventory
selector bits
bad-tail/loser expansion
source/fertility law
```

## Representative Output

For `n=4096,c=0.90,s=1`:

```text
P=1:    prefix coverage 0.500000, EOF coverage 1.000000
P=4:    prefix coverage 0.062500, EOF coverage 0.125000
P=16:   prefix coverage 1.526e-05, EOF coverage 3.052e-05
P=64:   prefix coverage 5.421e-20, EOF coverage 1.084e-19
P=1024: prefix coverage 5.563e-309, EOF coverage 1.113e-308
```

At fixed coverage, allowed average saving per pass tends to zero:

```text
c=0.90,P=64:   prefix <= 0.002375 bits/pass, EOF <= 0.018000
c=0.90,P=1024: prefix <= 0.000148 bits/pass, EOF <= 0.001125
```

## Single Relaxation That Remains Constructive

Relax content-blindness while preserving:

- stateless decode;
- losslessness;
- bounded loss;
- visible-state accounting;
- uniform negative controls.

The remaining constructive target is a predeclared public source/fertility law:

```text
frozen Q or public class F
measured c*
measured p_FF and p_OF
uniform controls negative
full on-disk accounting
```

This is not the strict "roughly all structure-free data" goal, but it is the
only remaining route that still resembles recursive Telomere rather than a
hidden selector.
