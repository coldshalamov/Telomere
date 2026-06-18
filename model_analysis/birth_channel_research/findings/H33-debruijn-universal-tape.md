# H33 - de Bruijn / universal tape addresses

Date: 2026-06-17

## Question

Can a public universal tape guarantee matches and avoid the salting/match-rate
problem?

Mechanism:

```text
public cyclic tape contains every L-bit string exactly once
record stores coordinate
decoder reads coordinate and copies L tape bits
```

This is stateless and deterministic.

## Coordinate cost

A de Bruijn cycle of order `L` has `2^L` positions. Naming every `L`-bit block
therefore needs:

```text
log2(2^L) = L bits
```

H33 examples:

```text
span L=16,  address=16 -> coverage=1,      net=0
span L=64,  address=32 -> coverage=2^-32,  net_if_hit=32
span L=64,  address=64 -> coverage=1,      net=0
span L=128, address=64 -> coverage=2^-64,  net_if_hit=64
span L=128, address=128 -> coverage=1,     net=0
```

Universal tapes guarantee matches by making the address space as large as the
span space. Shorter addresses are sparse-hit mechanisms, not all-data coverage.

## Overlap

Adjacent tape windows share bits. A run of `m` adjacent `L`-bit windows can be
described by one coordinate plus path length, requiring roughly `L + m - 1`
bits instead of `mL`.

This is real for sources constrained to adjacent tape paths. For arbitrary
independent windows, the missing source/order information is the difference:

```text
L=8,  m=16: raw=128, adjacent=23, source fraction=2^-105
L=16, m=16: raw=256, adjacent=31, source fraction=2^-225
L=16, m=256: raw=4096, adjacent=271, source fraction=2^-3825
```

So overlap is a source-shaped path prior, not a roughly-all-data compression
channel.

## Recursion and phase

Public phase shifts or alternative tapes can refresh which subset is visible.

- If the phase is fixed by pass, it is free but entropy-neutral.
- If the encoder chooses the best phase/tape, the decoder needs the selector:

```text
selector = log2(number_of_phases_or_tapes)
```

This reduces to H30/H15.

## Verdict

De Bruijn/universal tapes are a useful scaffold for stateless placement,
deterministic salt, and exact coverage tests. They are not a missing all-data
compression source:

- full coverage address cost equals raw span cost;
- shorter addresses have exponentially incomplete support;
- overlap is a public source prior/path constraint;
- phase choice is either fixed or paid.

## Artifact

`model_analysis/birth_channel_research/H33-debruijn_universal_tape.py`
