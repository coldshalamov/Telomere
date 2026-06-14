# BEST_SPEC: No Arbitrary-Content Winner Yet

Date: 2026-06-14

Status: reopened after anti-reward-hack review. No candidate currently satisfies
the arbitrary/unshaped content bar. The previous TST/STF/BBL stack remains a
set of controls and finite ledges, not a completed solution.

- **Typed Scheduled Tree (TST)** is a reachable-set positive control. It is deterministic,
  lossless, statelessly decodable, deep, and fully charged-positive in a
  generated reachable regime. Verified toy: depth 6, two roots, 128 leaves,
  `raw_bits=1024`, `charged_bits=917`, `net_bits=+107`.
- **Scheduled Forest (STF)** is the first fully charged-positive construction
  in the toy kernels: exact encode/decode, no birth tags, public open schedule,
  fresh depth/position salts, and charged-positive generated reachable
  fixtures at depth 2 and depth 3.
- **Bounded Bundle Layer (BBL)** is the many-pass extension path: it keeps fresh
  opportunities across a bounded pass window and prices open/carry ambiguity as
  `R*c_a(P)`, but the current toy fixture is positive only before fixed-header
  amortization.

Together they define useful mechanics, but not the requested answer. The active
research target is now arbitrary/unshaped match-supply maintenance without a
birth-pass channel.

## Anti-Reward-Hack Boundary

TST solves the stateless open/salt ordering problem for a scheduled generated
class. It does **not** prove that arbitrary content-blind inputs maintain a high
match rate.

The price is not hidden in final positions, holes, pass logs, or birth tags.
Those channels are absent or explicitly charged. The price is match supply:
only slabs in the recursive image of a root seed can use typed-tree mode.

At the verified depth-6 setting:

```text
raw bits per root slab = 512
seed bits per root     = 415
record bits per root   = 417
full seed-space coverage under uniform output ~= 2^(415 - 512) = 2^-97
```

So a uniform random 512-bit slab is overwhelmingly expected to fall back to raw.
The positive fixture is generated from reachable roots and then stores those
roots at full fixed width. That is a real codec/accounting proof for a
reachable generated regime, not a natural-corpus or arbitrary-random match-rate
claim.

## Current Research Name

Arbitrary-content freshness search: decoder-known nonces, target-refresh, and
self-dating grammar mutations.

## Active Lead: Arbitrary Freshness Kernels

Runnable kernel:

```powershell
python model_analysis\birth_channel_research\arbitrary_freshness_kernels.py
```

Current result: no arbitrary-content solution yet. The kernel produced three
useful constraints:

1. Decoder-known visible nonces decode statelessly and refresh dice, but their
   bits are paid as stored address width. In the toy, `k=3` raises hit
   probability to `0.125` but leaves only 1 gross bit per hit; `k>=4` reaches
   zero or negative gross savings.
2. Fixed-universe target refresh round-trips without pass salt or birth tags.
   On 200 random 96-block trials, pass-1 hit rate averaged `0.02863`, pass-2
   fell to `0.00070`, and pass-3 hit rate was zero. It gained `+8.460` bits
   against literal-wrapped working state but lost `-87.540` bits against the
   original payload, so wrapper accounting cannot be counted as compression.
3. Self-dating grammar residues reduce wrong-pass ambiguity, but they also
   lengthen every true target and shrink arbitrary hit supply. In the toy
   sweep at `P=1,000,000`, the best expected net per arbitrary window was only
   `6.018e-05` bits at arity 2 with 6 residue bits.

The next mutation should not add a bigger generated positive control. It should
combine a decoder-visible nonce that is already present in the final stream with
a target-refresh rule that does not expand the target language, or find a
self-dating grammar whose validity check is derived from existing item bits
rather than carried as extra residue.

## Candidate A: Typed Scheduled Tree

## Purpose

Remove the birth/open/carry problem by making node type and open time public.
At every depth, the decoder knows whether an expansion means child seeds or
literal bytes. The seed record is still shorter than the two scheduled children
it replaces, and every level uses a fresh hash context.

## TST State

- A slab is a fixed-depth binary forest.
- Each root seed represents `2^depth` literal leaves.
- At depth `1`, `expand(seed, depth, position)` emits two `B`-bit literals.
- At depth `d > 1`, `expand(seed, depth, position)` emits two child seeds of
  width `seed_bits(d-1)`.
- The decoder does not parse type markers from the expansion; type is supplied
  by the public depth schedule.
- Seed widths are tiered so local replacement remains compressive:

```text
seed_bits(1) = 12
seed_bits(d) = 2 * seed_bits(d-1) + 1
record_bits(d) = 2 + seed_bits(d)
record_bits(d) < 2 * record_bits(d-1), for d > 1
record_bits(1) < 2 * B
```

## TST Encode

1. Choose a public depth and root count.
2. Split the input into fixed groups of `2^depth` leaves.
3. For each group at root position `p`, search for a root seed whose recursive
   typed expansion exactly regenerates that group.
4. If every group has a root seed, emit typed-tree mode:
   `mode, depth, root_count, root_seed[]`.
5. If any group lacks a witness, emit raw fallback mode.

The toy positive fixture is generated from low root seeds, so the toy encoder
can find witnesses quickly. The root values are still stored at full fixed
width; there is no hidden low-seed side channel.

## TST Decode

1. Read `mode`, `depth`, `root_count`, and root seeds.
2. For each root at tree position `p`, recursively expand:
   - if `depth = 1`, interpret the hash prefix as two literals;
   - if `depth > 1`, interpret the hash prefix as two child seed integers and
     recurse to `depth - 1` at positions `2p` and `2p + 1`.
3. Concatenate leaves and verify the fixed checksum/root referee.

No open/carry search is performed because all openings are fixed by public
tree depth.

## TST Freshness

Every node uses a fresh SHA-256 domain separated by:

```text
salt = H_domain(node_kind, seed, depth, tree_position)
```

Depth and tree position change across recursive levels, so the same seed value
at different levels or positions has independent effective hash outputs.

## TST Accounting

Toy charged fields:

- 1 mode bit;
- 6 depth bits;
- 12 root-count bits;
- full fixed-width root seeds;
- 64-bit checksum/root referee.

Verified TST output:

```text
depth=4 roots=4 leaves=64  raw_bits=512  charged_bits=503  net_bits=+9
depth=6 roots=2 leaves=128 raw_bits=1024 charged_bits=917  net_bits=+107
```

Local budget table:

| depth | seed bits | record bits | child payload | local margin | raw/root |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 12 | 14 | 16 | 2 | 16 |
| 2 | 25 | 27 | 28 | 1 | 32 |
| 3 | 51 | 53 | 54 | 1 | 64 |
| 4 | 103 | 105 | 106 | 1 | 128 |
| 5 | 207 | 209 | 210 | 1 | 256 |
| 6 | 415 | 417 | 418 | 1 | 512 |

Price paid: reachable-set density and encoder search. Arbitrary inputs fall
back to raw unless the encoder finds a root-seed witness. Generated reachable
forests are the positive regime.

Runnable kernel:

```powershell
python model_analysis\birth_channel_research\typed_scheduled_tree_codec.py
```

## Candidate B: Scheduled Forest

## Purpose

Eliminate the open/carry problem by accepting only complete scheduled bundle
trees. Every internal node has a public depth, so the decoder knows exactly when
to open it and which salt to use.

## STF State

- A slab is a fixed-depth binary forest.
- Each root seed expands to two children at depth `d`.
- At depth `1`, children must be literals.
- At depth `>1`, children must be records that recursively satisfy the schedule.
- Salts are:

```text
salt = H_domain(depth, tree_position, seed)
```

## STF Encode

1. Split the slab into `root_count` fixed-size groups of `2^depth` blocks.
2. For each group at root position `p`, search for a seed whose recursive
   scheduled expansion exactly regenerates that group.
3. If every group has a root seed, emit forest mode:
   `mode, depth, root_count, root_seed[]`.
4. If any group fails, emit raw fallback mode.

No birth tags, hole coordinates, or per-pass logs are stored. The schedule is
public and the root count/depth are fixed/root fields.

## STF Decode

1. Read `mode`, `depth`, `root_count`, and the root seeds.
2. For each root at position `p`, recursively expand:
   - at depth `d`, compute `expand(seed, d, p)`;
   - if `d = 1`, require two literals;
   - otherwise require two child records and recurse at positions `2p` and
     `2p+1`.
3. Concatenate decoded leaves and verify the fixed checksum/root referee.

## STF Accounting

Toy kernel parameters:

- `B = 8`;
- seed field is depth-tiered: 15 bits at depths 1-2, 22 bits at depth 3;
- record item = 2-bit marker plus the depth's seed width;
- fixed/root fields = mode bit + 6 depth bits + 8 root-count bits + 64 checksum
  bits.

Verified generated forests:

```text
depth=2 roots=8 leaves=32 raw_bits=256 charged_bits=215 net_bits=+41
depth=3 roots=2 leaves=16 raw_bits=128 charged_bits=127 net_bits=+1
```

This is fully charged-positive in the toy. The price is reachability density:
arbitrary data usually falls back to raw. The current tiered toy reaches depth
3, but the margin is thin and root search is heavier.

Runnable kernel:

```powershell
python model_analysis\birth_channel_research\scheduled_tree_codec.py
python -c "import sys; sys.path.insert(0, r'model_analysis\birth_channel_research'); import scheduled_tree_codec as s; s.forest_demo(depth=3, roots=2)"
```

## Candidate C: Bounded Bundle Layer

## Purpose

Use only length-pinned bundle records during a bounded pass window. Avoid
arity-1 singles as the deep engine, because singles have no structural
open-pass subsidy and cost `log2(P)` bits per record. BBL accepts the finite
bundle subsidy as the birth/open channel and caps the pass count before that
subsidy is exhausted.

## BBL State

- The live stream is an ordered list of self-delimiting items.
- An item is either a literal block or a bundle record.
- A bundle record replaces exactly `a >= 2` contiguous live items with one
  seed record.
- The layer has fixed public parameters:
  - block size `B`;
  - arity set, preferably one arity for the first candidate, `a = 2` or `a = 3`;
  - maximum passes `P_max`;
  - shuffle family;
  - hash/expander domain;
  - checksum width or equivalent root referee.

## BBL Encode

For pass `t = 1..P_max`:

1. Scan the current packed stream for arity-`a` windows.
2. For each window at packed output position `j`, search compressive seed
   records.
3. A seed is eligible only if:
   - `expand(seed, t, j, a)` parses as exactly `a` self-delimiting items;
   - those items are byte-identical to the candidate window;
   - the seed record is shorter than the replaced window after all charged
     costs for the selected configuration.
4. Replace accepted non-overlapping windows greedily or by a deterministic
   selector.
5. Shuffle the packed stream with the public reversible shuffle.

Salt rule:

```text
salt = H_domain(layer_id, pass_index t, packed_record_position j, arity a)
```

The salt uses the packed record coordinate, not the pre-replacement hole
coordinate. This matters: the packed coordinate is what the reverse decoder can
observe after unshuffling.

Stop rule:

- For the candidate kernel, run a fixed `P_max`.
- For a production variant, a no-hit pass may stop the layer, but the stop
  condition must be derivable by reverse trial decode or stored as fixed/root
  layer data and priced.

## BBL Wire

Store:

- fixed/root header fields needed by the base Telomere format;
- layer parameters if not profile-fixed;
- final packed item stream;
- original length;
- fixed checksum/root referee.

Do not store per-record birth pass, per-record open/carry bit, hole coordinates,
or per-pass mutation logs.

## BBL Decode

Input: compressed bits plus fixed/root/end-state data.

For pass `t = P_max..1`:

1. Unshuffle the packed stream using the public inverse shuffle.
2. Walk the unshuffled stream.
3. For each literal, carry it.
4. For each record at packed position `j`, branch:
   - carry it unopened;
   - open it using `expand(seed, t, j, a)`, but only if the prefix parses as
     exactly `a` self-delimiting items.
5. Prune branches whose item count exceeds the original length or whose grammar
   is invalid.

After all reverse passes:

1. Keep candidates that are all literals and have the original length.
2. Use the fixed checksum/root referee to select the original.

The checksum is not free in the ledger. Its role is equivalent to selecting one
surviving reading among the parse-valid open/carry branches. The priced
asymptotic birth/open cost for `R` final bundle records is:

```text
ambiguity_bits = R * c_a(P_max)
c_a(P) = log2(1 + (P - 1) * 2^-E_a)
```

where `E_a = -log2(q_a)` and `q_a` is the wrong-salt parse-survival probability
for arity `a`.

## BBL Freshness

BBL refreshes hash opportunities because each pass changes at least one of:

- pass index `t`;
- packed position `j`;
- neighboring item windows after shuffle.

Therefore the same logical content can receive fresh effective SHA outputs on
later passes while the decoder can still reconstruct the correct salt when it
opens the record at the tested reverse pass.

## BBL Accounting

Per accepted bundle record:

```text
net_per_bundle = replaced_bits - record_bits - c_a(P_max)
```

For the Golden-style measured bundle ledger:

| arity | `E_a` bits | `P` with `c_a(P) < 2` | `c_a(64)` |
| --- | ---: | ---: | ---: |
| 2 | 9.36 | about 1,972 | 0.132 |
| 3 | 12.59 | about 18,497 | 0.015 |
| 4 | 14.97 | about 96,282 | 0.003 |
| 5 | 18.20 | about 903,374 | near 0 |

This gives a real bounded win in a dense reachable-bundle regime. Example:
with arity 2, `P = 64`, and gross selected-record win `2.17` bits, the charged
birth/open cost is `0.132` bits, leaving about `2.038` bits per accepted bundle
before fixed header amortization. For a dense generated corpus with many
accepted bundles and few leftovers, this is net-positive.

Whole-file caveat:

BBL does not make random data compress. Literal carriage and low base hit
density still dominate random/content-blind inputs. The candidate wins only in
the explicitly stated dense reachable-span regime: a population where exact
bundle windows are frequent enough that selected bundle savings exceed literal
carriage, fixed header, and ambiguity costs.

## Kernel

Runnable toy:

```powershell
python model_analysis\birth_channel_research\bounded_bundle_codec.py
```

The toy uses:

- 4-bit literals;
- fixed arity 2;
- 5-bit seeds;
- incomplete item grammar;
- SHA-256 expansion keyed by `(pass, packed_position, seed)`;
- reversible shuffle;
- DFS reverse decoder with no birth tags.

The default run now prints two fixtures:

- a random mechanics fixture, which round-trips over six passes and shows fresh
  matches but does not compress;
- a generated dense reachable-bundle fixture, which round-trips over two passes
  and is payload-positive after ambiguity pricing.

Current generated dense fixture output:

```text
blocks=24, passes=2
matches=13
payload_delta=+19.000 bits
asymptotic_delta=+11.918 bits after ambiguity pricing
charged_delta=-54.082 bits after the 66-bit toy header
```

This is the first concrete positive-control regime for BBL: the codec round
trips, the decoder receives no birth tags, and the dense generated population is
positive before fixed header amortization. It is still not a natural-density
claim. At larger scale or with chunked dense blocks sharing fixed/root data, the
header is amortized once the dense population supplies more than the fixed
referee/header bits.

## Mutations Tried

- Fixed-width Scheduled Forest: charged-positive at depth 2 but failed to reach
  depth 3.
- Tiered-width Scheduled Forest: succeeds at depth 3 by using the larger
  internal-node budget; depth-3 two-root forest is charged-positive by 1 bit.
  Superseded by TST, which removes internal marker entropy and reaches depth 6.
- Typed Scheduled Tree: succeeds as a reachable-set positive control by making
  child type public from the schedule and interpreting internal expansion bits
  directly as child seeds. It reaches depth 6 with `+107` fully charged bits in
  the toy, but it does not maintain arbitrary-content match supply.
- Pre-replacement anchor salt: failed in the toy because the packed decoder sees
  the record at its post-replacement packed coordinate. Fixed by salting with
  packed record position.
- Arity-1 singles: rejected as the deep engine because every wrong salt still
  parses as one item, giving exact ambiguity `P^R`.
- Final-position board: mechanically reversible when positions are stored, but
  the final arrangement note is the birth channel and costs `log2(valid final
  states)`.
- Biased seed/pass grammar: can encode birth bits in seed classes, but each bit
  costs at least one bit of match supply.

## TODO

1. Port TST's typed schedule into a SPEC_V1-compatible profile and decide
   whether public schedule-supplied child types are acceptable Telomere metadata
   or a hybrid mode.
2. Replace the toy seed-width recurrence with real Lotus/J3D1 costs and compute
   the exact local margin by depth.
3. Add an encoder search budget/throughput model for finding root-seed witnesses
   on non-generated data.
4. Combine TST and BBL: use TST where complete scheduled subtrees exist, then
   hand residual streams to BBL for bounded fresh-pass search.
5. Replace the toy arity-2 grammar with the real SPEC_V1/Lotus cost table in a
   small BBL kernel.
6. Upgrade the BBL generated dense fixture from "payload/asymptotic positive" to
   fully charged positive after fixed/root header amortization, with a chunking
   rule whose own boundaries are priced.
7. Implement a bounded BBL decoder with an explicit branch budget derived from
   `R * c_a(P)` rather than a generic state cap.
8. Test arity 3 and arity 4 BBL variants; they have much larger pass windows but
   lower natural hit supply.
9. Price whole-layer literal carriage for several dense regimes and identify
   the minimum accepted-bundle density needed for a kept layer.
10. Decide whether TST+STF+BBL is a Telomere mode or a hybrid/dense-class mode.
    Under strict content-blind random input, it is not a universal compressor.
