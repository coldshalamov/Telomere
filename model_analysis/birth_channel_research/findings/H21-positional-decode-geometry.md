# Avenue H21 - positional decode geometry

Author: Codex continuation from user prompt. Date: 2026-06-17.
Status: serious geometry lane; boundary-only variant needs a new invariant.

## HYPOTHESIS

The user proposed that the missing piece may be geometric rather than another
hash trick:

- the decoder tells from relative position how blocks were shuffled, what the
  salt is, and whether a block is ready;
- ready decoded blocks are compacted to the beginning of the stream, with a
  short boundary marker between ready and not-ready regions;
- decode order might not matter because all blocks converge to the right
  positions once fully decoded.

These are not the same as per-record birth tags. They are possible low-rate
state channels. H21 prices them instead of dismissing them.

## MECHANISM A: POSITION AS STATUS / SALT

Position-as-salt is already the cleanest free invariant when the position is
decoder-derived. If an item is at position `i` during the reverse pass, the
decoder can use `i` as the salt without storing it.

Position-as-status is different. A position lane can signal "ready" only if:

```text
ready(i, pass) = public predicate
```

Then no status bit is stored. But the encoder must either:

1. accept matches only in public ready-lane positions, losing match supply; or
2. move arbitrary content-hit records into ready positions, which encodes a
   subset/permutation and must be paid.

For a ready lane fraction `r`, the metadata-free supply loss is:

```text
log2(1/r) bits per eligible record
```

That is not automatically fatal, but it is the same currency as sparse-cover
entropy.

## MECHANISM B: READY PREFIX WITH A PER-PASS BOUNDARY

The attractive version:

```text
[ready/open records][not-ready carries]
              ^
          boundary
```

If a pass makes `m` records in a stream of `N`, storing only the boundary costs:

```text
log2(N + 1) / m bits per opened record
```

This can be tiny for large `m`. Example: `N=1,000,000`, `m=100,000` costs about
`0.000199` bits/opened record.

But boundary-only works only if the decoder does not need to undo a
content-dependent stable partition. If encode selected arbitrary hit positions,
then compacted those records to the front, the decoder needs the subset of
positions that moved:

```text
log2 C(N, m) / m bits per opened record
```

That is the hidden bitmap. The boundary tells the decoder how many records
opened, not where they came from.

So the ready-prefix idea needs one of these invariants:

1. **Prefix semantics:** the pass only creates records in a public prefix/lane,
   so previous-layer order is prefix expansion plus suffix carries. This is
   stateless, but spends match supply.
2. **Public stable-partition source:** the moved subset is public/derivable
   from positions, not from content hits. Again, this spends supply or
   restricts the search.
3. **Total-cover inside prefix:** if every item in the active region is
   rewritten, there is no sparse subset to restore. This returns to Total-Cover,
   with the witness stream as the remaining bill.

## MECHANISM C: ORDER-INDEPENDENT CONVERGENCE

Order-independent decode can work only if final records carry or derive their
coordinates. There are three variants:

- **Public coordinates:** coordinate is current position/orbit phase. Free, but
  only for records whose placement follows the public orbit.
- **Seed-derived coordinates:** seed expansion includes destination coordinate.
  Stateless, but coordinate bits consume seed entropy unless the source prior
  makes them correlated.
- **Multiset canonicalization:** decode produces a multiset and sorts by a
  public key. Free only if the original order is that public sort; otherwise it
  is a transform/source-prior claim.

If arbitrary original byte order must be recovered, coordinate information
cannot disappear. It is either derived from a public invariant or paid as an
arrangement channel.

## RUNNABLE LEDGER

`../H21-positional_geometry_ledger.py` prints the three relevant prices:

- boundary bits per opened record;
- honest subset bits per opened record;
- deterministic ready-lane supply loss per record.

Representative reading:

```text
N=1,000,000, r=0.10
boundary only = 0.000199 bits/record
subset layout = 4.689860 bits/record
hidden bits if boundary-only = 4.689661 bits/record
ready-lane supply loss = 3.321928 bits/record
```

The boundary is extremely cheap if it is really sufficient. The hard problem is
making it sufficient without hiding the subset.

## VERDICT

This lane is not dead. The promising shape is:

```text
public orbit/lane schedule
+ ready-prefix active region
+ per-pass boundary count
+ no content-dependent stable-partition inversion
```

The danger shape is:

```text
arbitrary sparse hits
+ stable partition to prefix
+ only boundary stored
```

That silently encodes `log2 C(N,m)` bits of hit layout.

The next kernel should test a **phase-lane Total-Cover hybrid**:

1. partition positions into public phase lanes;
2. on each pass, fully rewrite only the active lane and compact completed lane
   records to the prefix with one boundary;
3. require the inactive suffix to be carried in public order;
4. charge lane supply loss, boundary counts, and exact witness bits;
5. compare against Total-Cover and H4 sparse-layout rows.

This is the most faithful version of the user's idea: position tells the
decoder what is ready, the salt is self-presenting, and the only stored
per-pass state is a small boundary. It will cross only if the lane restriction
costs less than the birth/open entropy it removes.
