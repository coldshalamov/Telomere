# Avenue H23 - final-board coordinate decode

Author: Codex continuation with Bacon scout memo. Date: 2026-06-17.
Status: order-independent decode audit.

## HYPOTHESIS

Maybe decode order does not matter if every record mathematically lands in the
right place once fully decoded. This includes final-board/egg-carton ideas,
modular wrap, CRT clocks, affine/Feistel orbits, parity/sign lanes, and
position-derived salts.

## BEST MECHANISM

The best Telomere-compatible shape is a public final-board / phase-lane
Total-Cover hybrid:

```text
wire position or board slot f
public phase/lane/pass state p
public permutation P_p
child index j inside the expanded arity
destination = P_p^-1(tile(f, j))
```

Records may open in any computational order because placement is a pure public
function of slot ordinal, arity, child index, and phase. The record still has a
coordinate: its parsed board slot. The coordinate is free only because it is
the wire position or a public orbit coordinate the decoder already knows.

## DECODE

1. Parse the final board/list and assign each record its ordinal `f`.
2. Derive public phase/lane/pass state from the fixed schedule.
3. Expand the seed with the self-presenting position/phase salt.
4. Place children at public destinations.
5. Reject collisions, impossible parses, or checksum failures.

Within a known board state, opening order is irrelevant.

## STORED / DERIVED / HIDDEN

Public-derived:

- board size;
- block size and arity alphabet;
- seed order;
- phase/lane schedule;
- CRT/affine/Feistel/prime-walk permutation;
- slot ordinal;
- child offset inside bundle.

Stored:

- ordinary record bits `[arity][seed]`;
- literals if the branch permits them;
- fixed/root/end header and checksum.

Hidden if omitted:

- arbitrary sparse hit subset;
- record-to-destination permutation;
- content-dependent lane assignment;
- birth/pass salt not derivable from public phase;
- collision-resolution choices after modulo wrap;
- seed-derived coordinates not paid as extra match bits.

## COUNTING CHECK

For sparse arbitrary hits:

```text
N = 1,000,000
m = 100,000
r = 0.10
```

Boundary count:

```text
log2(N+1)/m ~= 0.000199 bits/record
```

Actual subset:

```text
log2 C(N,m)/m ~= 4.68986 bits/record
```

Coordinate-free bag order:

```text
log2(m!)/m ~= log2(m) - log2(e)
```

which is about `15.17` bits/record at `m=100,000`.

Seed-derived destination coordinates are also not free. Naming one destination
among `N` cells costs about `log2 N` additional match bits per record, because
the seed must match both payload and coordinate unless the coordinate is a
public function of the slot.

## SALT REFRESH

Position salts remain free only when the reverse decoder reaches the same
public pass state. A final-board decoder can refresh salts across phases if
phase/pass is public-derived.

A public `L`-phase lane schedule gives `L` salt domains. If `L` repeats, dice
repeat. If `L >= T` to avoid repeats for `T` passes, the active lane fraction
is about `1/T`, costing `log2 T` match-supply bits per record. That moves the
birth-tag bill into supply loss.

## VERDICT

Final-board/order-independent decode is mechanically possible and should not be
dismissed. The necessary invariant is:

```text
every record has a public slot coordinate
```

CRT, affine, Feistel, parity, and modular wrap are useful public permutations,
but they do not reveal content-dependent birth time or arbitrary hit layout.
They only rename public slots.

So this lane reduces to H22:

- public slots/lanes: stateless, priced by supply loss;
- arbitrary sparse compaction: hidden subset/permutation entropy;
- coordinate-free bags: hidden order entropy;
- seed-derived coordinates: extra match bits.

The next useful implementation, if revisited, is an exact `N<=12`
phase-lane final-board toy that randomizes decode order while placing children
by public slot. That would prove mechanics, not compression. The compression
ledger remains H22.
