# H26 - Value/count separation for position and seed classes

Date: 2026-06-17

## Question

Can a decoder learn open/carry state, pass salt, or placement from relative
position instead of from a stored ledger?

Examples:

- move ready records to the beginning of the stream and store one transition;
- put ready records in public lanes, residues, or board slots;
- use position as salt;
- let records decode out of order and land in public final-board coordinates;
- use a seed class or grammar whose stored seed tells the decoder the state.

## Best lawful mechanism

The strongest stateless form is a public active lane:

1. The root/header defines a public board, pass count, lane schedule, and child
   placement rule.
2. At a given pass, some public fraction `r` of positions are active.
3. Active positions always open. In Total-Cover form, the decoder reads records
   until the arity sum reaches the public active-lane atom count, so even the
   boundary can be derived.
4. The salt is `salt(pass, lane, public_position)` or just
   `salt(public_position)` if the schedule already encodes phase.
5. Decoded children are written to public coordinates. Decode order does not
   matter as long as every record's destination is public before expansion.

This is real. It is not a reward hack as a parser. The decoder knows open vs
carry because the lane is public, and it knows salt because the pass/lane/slot
schedule is public.

## The bill

The boundary is cheap only after the ready positions are public. For
`N=1,000,000` and `r=0.10`, a single boundary is only:

```text
log2(N+1)/(rN) = 0.000199 bits per opened record
```

But if the encoder first selected arbitrary content-dependent hits and then
compacted them to the front, the boundary hides the subset layout:

```text
H2(r)/r = 4.689956 bits per opened record at r=0.10
```

If the ready positions are public, that subset map disappears, but the eligible
match supply also shrinks to fraction `r`. The supply cost is:

```text
log2(1/r) = 3.321928 bits per opened record at r=0.10
```

So the position trick is a clean state channel, not a free compression channel.

## Value/count separation target

Under uniform hash, a decoder-visible seed or position class that conveys `b`
state bits occupies fraction `2^-b` of the eligible supply. That spends `b`
match-supply bits, the same price as storing `b` explicit bits. With the
current rough gross saving of `g = 2` bits per sustained match:

```text
net = g + value_lift - b
```

For `T=64` possible salts/passes, `b=6`, so a public class needs:

```text
value_lift > 4 bits per selected record
```

For the `r=0.10` ready lane, it needs:

```text
value_lift > 3.321928 - 2 = 1.321928 bits per opened record
```

For unbounded recursive passes, the value lift must scale at least one-for-one
with the state bits:

```text
E[value | decoder-visible class] - E[value] >= log2(1/class_fraction)
```

with strict margin if the goal is growth rather than merely not losing.

## Biology-shaped interpretation

This is the closest current mathematical analogue to the DNA intuition. A
biological developmental context is not a uniform hash class. A locus can be
decoder-visible by position and also unusually valuable because it participates
in repeated, regulated, pleiotropic unfolding. In Telomere terms, that would be
a public class whose count is small but whose downstream value is high.

That is exactly the missing piece: not "another marker", but a public
developmental/fertility field where value and count separate.

## Verdict

Position, lanes, boundaries, and out-of-order board placement are promising
decode geometry. They can solve stateless parsing:

- open vs carry is public;
- pass/salt is public;
- placement is public;
- no birth-pass ledger is needed.

They do not, by themselves, maintain the match rate. Uniform hash accounting
spends one supply bit for every visible state bit. The next target is therefore
constructive and precise:

> Exhibit a Telomere-compatible public class, lane, or grammar where selected
> records are more compressive by more than the supply fraction it removes.

Until that value/count separation is shown, relative-position tricks remain a
valid parser and salt scheduler, not a compression breakthrough.

## Artifact

`model_analysis/birth_channel_research/H26-value_count_separation.py`
