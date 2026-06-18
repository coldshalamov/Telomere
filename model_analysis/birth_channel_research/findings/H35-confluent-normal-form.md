# H35 - Confluent normal form / order-independent decode

Date: 2026-06-17

## Question

Can records decode out of order and still end up in the right positions without
a per-record placement ledger?

Mechanism:

```text
records open in any order
public local moves commute/sort/rectify them
decoder reaches a canonical normal form
```

This is the algebraic version of a ready/not-ready boundary, a stable
partition, trace-monoid commutation, or RSK/plactic-style rectification.

## Decoder observations

This family is real decoder machinery:

- open vs carry can be public if every record opens in the layer;
- birth pass can be public if the layer is total-cover;
- decode order can be irrelevant if the combination/normalization rule is
  public and confluent.

The compression question is whether arbitrary original order/placement is still
recoverable.

## Ready boundary

A single boundary marker is cheap only if the ready records are already a public
prefix. If the encoder chose an arbitrary ready subset of size `m` among `N`
slots, the hidden subset is:

```text
log2 C(N,m)
```

H35 examples:

```text
N=1,000,000, m=10,000:  boundary=19.932 bits, subset=80,785.174 bits
N=1,000,000, m=100,000: boundary=19.932 bits, subset=468,986.039 bits
N=1,000,000, m=500,000: boundary=19.932 bits, subset=999,989.708 bits
```

So a short delineation marker is valid only when readiness is determined by a
public invariant, not by which records happened to match.

## Linear extensions

A confluent normal form collapses many possible orders to one canonical order.
For lossless arbitrary streams, the missing object is the linear-extension
index:

```text
order_bits = log2(number of valid linear extensions)
```

For disjoint public chains of lengths `c_i`:

```text
order_bits = log2(m!) - sum_i log2(c_i!)
```

H35 examples:

```text
16 unordered distinct items: 44.250 bits = 2.766 bits/item
64 unordered distinct items: 295.995 bits = 4.625 bits/item
128 unordered distinct items: 716.162 bits = 5.595 bits/item
128 items in eight 16-chains: 362.161 bits = 2.829 bits/item
```

This is the same conservation result as H27, but generalized to partial-order
normal forms.

## Repeated values

Repeated values reduce order entropy:

```text
order_bits = log2(m! / prod_v count_v!)
```

But for arbitrary streams the remaining order index is still real. Treating the
stream as a multiset is a source prior, not a roughly-all-data Telomere
mechanism.

## Seed-derived placement

If the seed/hash output must self-describe a destination, phase, or lane, the
match predicate is stricter:

```text
expected_hits = searched_seeds / 2^(payload_bits + placement_bits)
```

Each placement bit omitted from the stream is lost as one bit of match supply.
H35 examples:

```text
payload=64, search=2^80, placement=0:  log2 E_hits = 16
payload=64, search=2^80, placement=8:  log2 E_hits = 8
payload=64, search=2^80, placement=16: log2 E_hits = 0
```

## Verdict

Confluent decode is excellent machinery for stateless placement. It does not
create an unpriced compression channel under the uniform hash law:

- public placement is free but carries no content-dependent signal;
- arbitrary ready subsets cost `log2 C(N,m)`;
- arbitrary order costs linear-extension entropy;
- seed-derived placement reduces hit supply by the same number of bits.

This collapses to H21/H23/H27 unless paired with a separate value/count
separation mechanism that can prove more than one future bit of value per paid
placement bit.

## Artifact

`model_analysis/birth_channel_research/H35-confluent_normal_form.py`
