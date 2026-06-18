# H32 - Bits-back latent seed reservoir

Date: 2026-06-17

## Question

Can cover ambiguity become a reusable salt reservoir across recursive passes?

Proposed mechanism:

```text
Q_p(x) = sum_z 2^-L(z) [expand(z)=x]
encode x with bits-back latent-cover code
recover posterior/latent tape
salt_{p+1}(position) = H(recovered_tape_p, position, pass)
```

This combines H29's collective cover marginal with H30's public dither/freshness
scaffold.

## Accounting

Bits-back is the right implementation for latent cover coding: it avoids paying
a selected-cover rank and achieves the marginal `-log2 Q(x)` up to finite ANS
state/start/end tape.

But the posterior tape is conserved state. If it is spent to choose among salts
or transforms, that bit has opportunity cost unless it is returned at the end or
creates more than one bit of future value.

H32 toy rows:

```text
passes=64,   gap/pass=0.0, tape=64, salt=64, gamma=1.0 -> net=0.0 conserved
passes=64,   gap/pass=0.5, tape=64, salt=64, gamma=1.0 -> net=-32.0
passes=1024, gap/pass=0.5, tape=64, salt=64, gamma=1.0 -> net=-512.0
```

Positive rows only appear when:

```text
gamma > 1
```

for example:

```text
passes=64, gap/pass=0.5, gamma=1.2 -> positive
```

That is the H28 fertility premise, not a free bits-back reservoir.

## Decode order

The reverse decoder can recover posterior tape from one layer and use it for
the next reverse layer only if:

- layer/pass order is fixed;
- the bits-back state is part of the final stream or bootstrapped and settled;
- salts are consumed in a public canonical order;
- final unused tape is stored or subtracted from gain.

Those are engineering constraints, not impossible ones. They do not change the
information ledger.

## Verdict

H32 collapses cleanly to:

```text
H29 collective marginal code
+ H30 public dither/freshness scaffold
+ H28 fertility condition for positive value
```

It is a strong implementation shape if a source-shaped fertility class is found.
It is not an all-data uniform-hash solution because tape bits are conserved and
best-of-salt use costs the bits it consumes.

## Artifact

`model_analysis/birth_channel_research/H32-bits_back_reservoir.py`
