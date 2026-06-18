# H41 - position / ready-prefix / compaction channel

Date: 2026-06-17

## Question

Can the decoder use relative position, shuffled order, or a ready-prefix
boundary to know which records should open, which salt to use, and where the
decoded blocks belong?

Mechanisms tested:

```text
[ready/open records][not-ready records]
              ^
          one boundary

public board/orbit position -> salt/pass/lane
decoded pieces settle into public destinations
```

This reopens the user's position-as-state idea. It does not assume the old
final-board/egg-carton variants are dead; it prices the hidden channel.

## Decoder observations

A decoder can know a salt for free when the salt is a public function of the
state it has already reached:

```text
salt = H(seed, public_phase, current_slot)
destination = public_function(record_ordinal, phase, child_index)
```

That makes position excellent stateless decode machinery. The compression
question is whether the encoder chose the ready/open set after seeing content.

## Ready prefix

A single boundary only says how many records are in the prefix. If membership
is public, that can be enough. If membership is a content-selected subset, the
hidden inverse stable partition is:

```text
log2 C(N,R)
```

H41 rows:

```text
N=1,000,000,R=100,000: boundary=19.932 bits, subset/R=4.689860 bits
N=1,000,000,R=900,000: boundary=19.932 bits, subset/R=0.521096 bits
N=1,000,000,R=999,000: boundary=19.932 bits, subset/R=0.011413 bits
```

So the boundary idea becomes powerful only in a near-total-cover regime. At
10% sparse replacement it is just a hidden bitmap.

## Birth/pass cohorts

If records are sorted into pass cohorts and only cohort counts are stored, the
counts are cheap but the original slot-to-cohort assignment is not. Equal
cohorts cost about `log2(P)` bits per atom. Near-total rewrite is different:
only rare exceptions need a cohort ledger.

H41 rows:

```text
P=64, old fraction=0.100: assignment=1.066305 bits/atom
P=64, old fraction=0.010: assignment=0.140252 bits/atom
P=64, old fraction=0.001: assignment=0.017175 bits/atom

P=256, old fraction=0.010: assignment=0.159722 bits/atom
P=256, old fraction=0.001: assignment=0.018802 bits/atom
```

This is the best constructive reading of the user's all-block replacement
instinct: do not store a sparse open map; drive the uncovered set toward zero.

## Final board / orbit phase

If the compacted wire has positions `0..R-1`, final position carries no extra
birth information. If the board holes or coordinates are observable, their
entropy is the paid position note:

```text
occupancy only:        log2 C(Q,R)
ordered positions:     log2 P(Q,R)
coordinate per record: log2 Q
```

H41 rows:

```text
Q=1,000,000,R=100,000: holes/R=4.689860, ordered/R=19.856902
Q=1,000,000,R=900,000: holes/R=0.521096, ordered/R=18.857978
```

Single-speed public orbits reveal total phase, not birth pass:

```text
final_pos = sigma^P(x)
```

which is independent of birth `t`. A freeze/slow-after-birth orbit can make
phase depend on `t`, but then the final coordinate is the birth ledger; reverse
decode also needs to know which items were live or frozen to invert the motion.

## Seed-derived placement

If the hash expansion must reproduce both payload and destination, every
destination bit is paid as lost match supply:

```text
expected_hits = 2^search_bits / 2^(payload_bits + placement_bits)
```

H41 rows:

```text
payload=64, search=80, placement=0:  log2 E_hits=16
payload=64, search=80, placement=16: log2 E_hits=0
payload=64, search=80, placement=32: log2 E_hits=-16
```

## Verdict

Position/compaction is not dead. The honest constructive shape is:

```text
public lane/prefix membership
+ all-open active region or near-total cover
+ public child placement
+ public phase/position salt
+ rare exceptions or a paid exception stream
```

The danger shape is:

```text
content-dependent sparse hits
+ stable partition to a prefix
+ only one boundary stored
```

That secretly stores `log2 C(N,R)`.

The next scientific target is therefore not "can a boundary be small?" It is:

```text
Can Telomere drive coverage close enough to total that the exception ledger is
below the available per-record win, while the witness stream remains paid and
parseable?
```

## Artifact

`model_analysis/birth_channel_research/H41-position_ready_compaction.py`
