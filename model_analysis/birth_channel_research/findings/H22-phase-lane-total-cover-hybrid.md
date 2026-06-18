# Avenue H22 - phase-lane Total-Cover hybrid

Author: Codex continuation from H21. Date: 2026-06-17.
Status: optimistic positional-geometry ledger.

## HYPOTHESIS

H21 showed that a ready-prefix boundary can be nearly free, but moving
arbitrary sparse hits into the prefix hides a subset map. The strongest
version of the user's idea is therefore:

```text
public phase lane says which positions are ready
every active lane slot opens
one boundary/count separates ready lane records from carried suffix
decoder interleaves by the public lane schedule
```

This removes open/carry/birth maps by geometry, not by metadata.

## MECHANISM

Runnable ledger:

- `../H22-phase_lane_total_cover_hybrid.py`

The kernel starts from the H3/H4 sparse bundle economics and replaces sparse
cover-layout entropy with:

```text
lane supply loss = q * log2(1/q) bits/input atom
boundary cost    = log2(N+1) / N bits/input atom
```

where `q` is the selected record density. This is the public-lane cost of
requiring all openings to occur in deterministic lane slots.

## IMPORTANT ASSUMPTION

H22 is an optimistic upper bound. It is valid only if **every active lane slot
opens**. If some active lane slots carry and others open, the decoder again
needs an intra-lane subset bitmap:

```text
log2 C(lane_size, opened_slots)
```

So a real phase-lane codec must either:

- use Total-Cover/literal-witness fallback inside the active lane; or
- prove another public all-open invariant.

## RESULT

The most interesting mathematical fact is that public lanes can beat arbitrary
sparse layouts by at most about the low-density combinatorial premium:

```text
H2(q)/q - log2(1/q) -> log2(e) ~= 1.4427 bits/record
```

That is real, but finite. The lane trick can remove a bitmap premium; it cannot
erase witness entropy.

Run:

```text
python model_analysis\birth_channel_research\H22-phase_lane_total_cover_hybrid.py
```

Best default-grid row:

```text
arity = 5
passes = 64
selected records/input atom = 0.00000095367
optimistic gross gain = 0.00000286075 bits/input atom
H4 layout-only gain = -0.0000175885 bits/input atom
phase-lane gain = -0.0000361442 bits/input atom
```

The phase lane is slightly worse than H4's ideal sparse layout in the nearest
row because the record density is so tiny that the one boundary over the
modeled file is not completely free. At larger densities, deterministic lane
loss can be cheaper than a full arbitrary subset map, but the gross bundle
economics have already turned negative.

## DECODE STORY

Decoder state is public:

```text
phase p
lane predicate lane(i,p)
boundary/count b_p
```

Decode reads the ready lane records, expands them using position-derived salt,
and interleaves the results back into the public lane positions. The inactive
suffix carries in public order. No per-record birth tag or sparse map is
needed if the all-open lane invariant holds.

## VERDICT

This lane was worth testing because it captures the user's positional intuition
without cheating. Under the current H3/H4 sparse bundle economics, the
optimistic phase-lane rescue does **not** cross. The missing proof is not the
boundary; the boundary is cheap. The missing proof is the all-open active lane:

```text
Can the active lane be fully rewritten at a paid cost below the arbitrary sparse
layout plus birth/open tax?
```

In this ledger, the answer is no for the sparse finite-K bundle branch. A
different phase-lane mechanism would need to improve the gross match/witness
economics, not merely replace the sparse layout with a public ready lane.
