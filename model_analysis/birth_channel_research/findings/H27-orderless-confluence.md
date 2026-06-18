# H27 - Orderless and confluent decode

Date: 2026-06-17

## Question

Can decode order stop mattering so that pass, placement, or ready/open metadata
does not need to be stored?

Variants:

- records expand in any order and children land in public final-board slots;
- records expand into a multiset and are sorted by public key;
- a commutative or confluent rewrite system reaches one normal form;
- seed-derived sort keys implicitly restore the original stream order.

## Best lawful mechanism

The strong stateless form is still public-coordinate decode:

```text
destination = public_function(record_ordinal, pass_or_lane, child_index)
salt        = public_function(pass_or_lane, record_ordinal)
```

Then computational opening order is irrelevant. The decoder observes wire
ordinal, arity, seed witness, public board size, lane/phase schedule, and
cumulative arity. The coordinate is free because it is the parsed wire slot or
another public slot already known before expansion.

This is mechanically valid and belongs with H23/H26.

## The order bill

If children are only a bag, arbitrary byte streams still need an order. For
mostly distinct records, recovering that order costs:

```text
log2(m!)
```

or per record:

```text
log2(m!) / m ~= log2(m) - log2(e)
```

At `m=1,000,000`, this is:

```text
18.488885 bits per record
```

If atom values collide and only value order matters, the bill is the
multinomial order entropy:

```text
log2(m! / prod_v count_v!)
```

For uniform 4-bit atoms at `m=1,000,000`, that is still almost:

```text
3.999863 bits per atom
```

For uniform 8-bit atoms:

```text
7.998145 bits per atom
```

So multiset canonicalization is basically a full order/source model. It is
valid only if the target representation is order-insensitive or already in the
public canonical order.

## Seed-derived sort keys

Sorting by seed/key does not make the order free. There are three equivalent
ways to pay:

1. Store the permutation.
2. Require random seed keys to appear in the target order, whose probability is
   `1/m!`, costing `log2(m!)` match supply.
3. Restrict the source to strings already sorted by that public key, which is a
   source-shaped/non-uniform premise.

Low-bit keys only move the bill into collision buckets and tie-breaking.

## Active lane plus orderless children

A public active lane solves open/salt state, but if children inside the lane are
unordered, the within-lane order entropy remains large. In the H27 ledger with
`N=1,000,000`, the sum:

```text
log2(1/r) + log2((rN)!)/(rN)
```

is nearly constant across lane fractions. For `r=0.10`:

```text
lane supply loss     = 3.321928 bits
within-lane order    = 15.167042 bits
lift needed to cross = 16.489 bits per opened record
```

Slicing into lanes does not make arbitrary order cheap; the lane-loss term and
the within-lane permutation term mostly trade places.

## Verdict

Orderless/confluent decode is useful only as mechanics:

- public slots make opening order irrelevant;
- public canonical order is free only for already-canonical data;
- arbitrary order requires a permutation/order channel;
- seed-derived ordering spends the same entropy as match supply.

This does not solve maintained recursive compression on roughly all data. The
surviving stateless scaffold remains:

```text
public final-board / active-lane Total-Cover
+ position-derived salt
+ public child placement
+ no content-selected compaction
```

Compression still needs the H26 missing piece: a public class or lane whose
selected records have value lift exceeding its supply loss.

## Artifact

`model_analysis/birth_channel_research/H27-orderless_confluence_ledger.py`
