# BEST_SPEC: No Arbitrary-Content Winner Yet

Date: 2026-06-14

Status: reopened after anti-reward-hack review. No candidate currently satisfies
the arbitrary/unshaped content bar. The previous TST/STF/BBL stack remains a
set of controls and finite ledges, not a completed solution.
Under the updated finish condition, completion would require a configuration
that can maintain compression over many passes and theoretically reach about
50% compression on arbitrary/random data. No current candidate meets that bar.

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

Current result: no arbitrary-content solution yet. The kernel produced these
useful constraints:

1. Decoder-known visible nonces decode statelessly and refresh dice, but their
   bits are paid as stored address width. In the toy, `k=3` raises hit
   probability to `0.125` but leaves only 1 gross bit per hit; `k>=4` reaches
   zero or negative gross savings.
2. Public nonce lanes avoid storing the lane id, but the decoder must try the
   lanes. In the exact toy, `K=8` lanes produced 5 records but at least
   `200000` surviving decode candidates, so the charged net was `<= -26.610`
   bits against raw payload.
3. Left-neighbor/packed-position context salts are genuinely decoder-visible
   without stored nonce bits. The exact toy round-tripped all sampled streams,
   but supply died after pass 1: pass-1 hit/window `0.01316`, pass 2 zero,
   mean payload gain `-19.250` bits. A full left/right-neighbor version was
   rejected because the right neighbor can change when later adjacent spans are
   replaced, so the decoder cannot derive the same nonce.
4. Fixed-universe target refresh round-trips without pass salt or birth tags.
   On 200 random 96-block trials, pass-1 hit rate averaged `0.02863`, pass-2
   fell to `0.00070`, and pass-3 hit rate was zero. It gained `+8.460` bits
   against literal-wrapped working state but lost `-87.540` bits against the
   original payload, so wrapper accounting cannot be counted as compression.
5. Arity-flex target refresh with arities 2-5 created a few longer-span hits
   but still stalled by pass 2 and lost `-92.895` bits against original
   payload.
6. Full-cover bundle lattice takes the "replace every block" idea literally:
   every output unit is a seed record, so the decoder needs no birth pass or
   open/carry bitmap. The exact toy searches every interval up to arity 6 and
   runs an optimal shortest-path cover. Rows that can cover require bloat:
   `net/record=-2` covers `0.880` of trials while losing `-30.148` bits, and
   `net/record=-1` covers `0.085` while losing `-17.647` bits. The first
   non-bloating row (`net/record=0`) produced no full covers in 200 trials
   with expected cover count `8.716e-04`; positive rows were far smaller.
   A fixed 3-byte seed table over 3-byte base blocks gives arity-5 hit/window
   probability only `1.262e-29`. Full replacement solves ordering, but
   profitable full-cover tilings are too sparse under the uniform hash law.
7. Adaptive smallest-replacement cover lets every interval use the smallest
   seed width found, then chooses the cheapest all-record tiling. This matches
   the "bloating singles can later be beaten by bundles" intuition. In the
   exact toy, the invalid free-width oracle is positive (`+12.955` bits on
   144 raw bits), proving the order-statistic effect exists. The valid
   width-paid ledger stores the variable seed-width class and flips to
   `-50.640` bits. The missing channel is the seed-width/rank boundary.
   The recursive adaptive-cover churn variant applies this all-record cover to
   its own serialized record stream. It round-trips `80/80` with no open/carry
   map and no birth-pass salt, so decode mechanics are not the failure. But
   144 random bits grow to `881.663` payload bits plus a `15`-bit charged
   pad-count/layer header after six passes, about `1.35x` growth per layer.
   Target churn alone amplifies the paid address-width margin instead of
   flipping it.
8. Overlapping-option seed-rank crossover models the 1+2+3+4+5 choices per
   interior block directly at 3-byte block scale with unlimited compute. Under
   an invalid `log2(first_rank)` oracle, max arity 5 gives `15` options/block,
   `+0.279` bits/block at 3 overhead bits, and a crossover near `3.876`
   overhead bits/record. The finite-depth version corrects the "must search
   15 bytes" intuition: with 3-byte blocks and max arity 5, the invalid oracle
   crosses earlier, around 92-96 search bits, because 3-block intervals are
   saturated and 4-block intervals begin to overlap enough; the 120-bit/15-byte
   row is near the asymptotic oracle (`+0.279` bits/block). But the parseable
   fixed-width ledger at 120 bits is negative (`-2.604` bits/block), and the
   selected-rank entropy lower bound is still negative (`-0.423`, or `-1.477`
   with 3 marker bits). The overlap crossover is real only if seed-rank
   length/termination is free.
   A block-local restatement confirms the intended "15 options touching each
   block" model rather than the naive one-5-block-bundle framing: at 120 search
   bits, each block sees about `13.106` finite matching options and `1.754`
   individually compressive options; a legal non-overlapping cover still has
   oracle gain `+0.283` bits/block. The failure is not the crossover intuition.
   The failure is still the paid witness boundary (`-0.430`, or `-1.496` with
   marker bits).
9. Collective selected-rank entropy coding gives the rank-witness idea a
   stronger paid lower bound: let the oracle DP choose the best tiling, then
   entropy-code selected `(arity, floor(log2 rank))` symbols under a public
   selected distribution and emit raw lower rank bits inside each bin. It still
   loses: max arity 5 has oracle `+0.297` bits/block but selected-rank entropy
   lower bound `-0.423`, or `-1.489` with a 3-bit marker. The selected witness
   distribution helps, but exact rank values still cost too much.
10. Recursive full-cover overlap dynamics projects the all-block replacement
   scheme over many passes. Since every parser unit is a seed record, open/carry
   and birth pass are genuinely irrelevant; under uniform hashes, the
   reserialized next pass is just another random target stream. The invalid
   oracle ledger shrinks from 14,400 bits to 6,845.9 bits after 64 passes and
   crosses half-size after about 59.7 passes. The paid ledgers immediately
   grow: ideal geometric rank reaches 103,230.8 bits by pass 64,
   selected-rank entropy lower bound reaches 44,358.3 bits, and
   selected+marker reaches 687,614.0 bits. Target churn amplifies the honest
   one-pass margin; it does not change its sign.
11. Whole-cover ordinal language encodes the selected cover as one ordinal in a
   public cover language, removing local rank terminators entirely. Exact toy:
   with 18 raw bits, `maxA=3, rank=2` has `log desc=13.579`, covers only
   `1.062%` of outputs, and saves `0.04697` expected bits before fallback
   tags; `maxA=3, rank=3` covers `22.074%` but has `log desc=18.844`, already
   larger than raw. The ordinal is just a generated codebook; coverage grows
   only as ordinal entropy grows.
12. Whole-cover referee-as-codeword replaces the ordinal with checksum bits and
   asks the decoder to enumerate the cover language. In the exact toy
   (`2785` generated outputs, `1.062%` coverage), short referees remain
   ambiguous (`ref=8` leaves `12.055` survivors), and nearly unique referees
   approach raw (`ref=16` has `1.040` survivors, saves only `2` bits/hit, and
   gives `-0.97875` expected bits with a raw fallback tag). A referee is just
   another codeword for the generated output.
   The global-referee interval-cover mutation scales that idea to the overlap
   language and stores only one end checksum/referee. It does not rescue the
   15-option crossover: with 600 3-byte blocks, arity-5-only 120-bit search has
   `0.63212` coverage but a half-size 7200-bit referee leaves about
   `2^7199.3` survivors; arity-5-only 48-bit search makes the half referee
   unique, but coverage is only `2^-8640`. Global end notes are the same
   witness entropy in another location.
   A canonical-minimum-cover rule can deduplicate multiple descriptions for the
   same output, but still must identify which canonical output is meant. In the
   exact 18-bit toy, `maxA=3, rank=2` drops from `13.579` description bits to
   `11.443` unique-output bits, but a half-size 9-bit code covers only
   `0.00195` of raw inputs. In the 600-block asymptotic counter, broad
   overlap languages still have best half-size canonical coverage `2^-7200`;
   narrow arity-5/48-bit coverage is `2^-8640`.
13. Global fixed-depth rank cover stores one decoder-known rank width in the
   root/header schedule, so per-record seed-width terminators disappear. This
   also fails: low widths cover with bloating short records, while high widths
   make longer bundles available but charge that width to every selected
   record. In the optimistic raw-fallback ledger with 3-byte blocks, max arity
   5, and 3 overhead bits, tested widths 24-120 all stayed non-positive; the
   best shown rows were `rank_bits=100` at `-1.750` bits/block and
   `rank_bits=120` at `-2.627`.
14. Homophonic literal recoding gives each payload block multiple reversible
   surface encodings, so the encoder can choose synonym bits that match a seed
   while the decoder strips them. Exact toy: value bits 4, scheduled pairs,
   6-bit seeds. Synonym widths 0-4 all had the same theoretical hit/pair
   probability `0.22158`; measured hit/pair stayed around `0.21-0.22`, while
   net worsened from `-22.658` at synonym 0 to `-424.810` at synonym 4.
   Surface-choice multiplicity cancels against the extra synonym bits; misses
   become longer.
15. Global public transform selection is the optimistic target-refresh version:
   choose one reversible public transform for a whole layer, store its index
   once, then encode scheduled slots under the fixed seed universe. It raised
   hit rate from `0.06232` at `K=1` to `0.08750` at `K=256`, but charged net
   worsened from `-26.445` to `-28.113` bits on 3072-bit random layers. The
   ideal large-deviation ledger stays negative after transform-index and
   bitmap entropy are priced, so per-window transform choice would only add a
   larger coordinate bill.
16. Whole-layer rechunk/superposition target refresh gives the idea its clean
   stateless form: fixed unsalted universe, known layer count, prefix tokens,
   and greedy matching at every bit position. It round-tripped `200/200`, but
   boundary visibility moved into literal tokens. On random 192-bit inputs,
   pass 1 averaged `6.105` matches yet bloated to `280.21` bits (`-88.215`
   versus original), and six passes averaged `4756.83` final bits
   (`-4564.830` versus original).
   The adaptive-length version lets each layer choose public chunk length
   `(10,12,14)` with only a 2-bit layer index. It always chose the least-bad
   14-bit mode in the focused run, bloating 512 random bits by `-183.125`
   final visible bits over five passes; tight nets stayed around `-6.7`
   bits/layer. Closed-form options all lose after bitmap entropy (`-0.31128`,
   `-0.08729`, `-0.02237` bits/slot), so effective-length migration is not a
   fixed-universe compression attractor.
17. Public-shuffle scheduled target refresh changes adjacency without salt:
   each pass applies a decoder-known bit permutation, then encodes fixed
   scheduled chunks. The exact toy round-tripped `200/200` and maintained
   hit/chunk near the fixed universe rate over eight passes (`0.06292`,
   `0.06315`, `0.06160`, `0.05990`, `0.05901`, `0.06423`, `0.05695`,
   `0.05454`). It still lost: visible chunk tokens grew 512 random bits to
   `777.50` bits after eight passes (`-265.495` versus original), and the
   tighter scheduled-bitmap ledger was negative on every layer, ending at
   `-7.540` bits versus that layer input. Adjacency refresh works, but
   open/carry remains a paid bitmap.
18. Decoded-left-context nonce refresh uses the previous decoded chunk as the
   salt for the next chunk in public-shuffled order. The encoder knows that
   left neighbor while matching, and the decoder knows it before opening the
   current chunk. This is a stable neighbor-identity nonce, unlike a future
   right neighbor. The exact toy round-tripped `60/60`; hit/chunk stayed near
   the 9-bit seed context rate across four passes (`0.02963`, `0.03962`,
   `0.03298`, `0.02878`). It still lost: visible tokens grew 512 random bits
   to `643.82` after four passes (`-131.817`), and the tight bitmap ledger
   stayed around `-4.6` to `-5.3` bits/layer. One active neighbor context does
   not multiply arbitrary hit supply.
   The context-lane validity hybrid derives lane bits from that same causal
   neighbor before opening and stores only local seed bits. It round-tripped
   all tested lanes (`0,2,4,6,8,10`) over 3 passes, but each lane bit simply
   halves eligible seed supply. The closed uniform ledger stays negative
   (`lane 0: -0.08729`, `lane 4: -0.00562`, `lane 10: -0.00009` bits/slot),
   and the exact toy still bloats visibly and under tight bitmap accounting.
   Checkerboard two-neighbor context makes the right neighbor stable by
   carrying the opposite parity as literal guard chunks. This gives a genuine
   decoder-known left/right nonce before active expansion and round-trips
   (`20/20` over four passes), but half the slots are forced guards and the
   active half still has only one context per slot. With 14-bit chunks and
   9-bit seeds, the closed active-slot ledger is `-0.04437` bits and the
   all-slot ledger is `-0.02219`; the exact toy loses `-28.750` visible bits
   after four passes and `-2.2` to `-2.9` tight bits per layer.
19. Selected public-shuffle hitmap shaping lets the encoder try `K` public
   shuffles and pick the best lower-bound hitmap ledger, then stores the
   shuffle index once. It round-trips exactly and does increase hits: pass-1
   hit/chunk rose from `0.06134` at `K=1` to `0.16644` at `K=64`. But the
   shuffle index and remaining bitmap entropy consume the gain. The favorable
   lower-bound ledger worsened from `-5.896` bits at `K=1` to `-7.333` at
   `K=64`; visible-token net improved but remained negative (`-27.167` to
   `-12.033`). Choosing nicer public coordinates is still a paid channel.
20. Prefix-parse-state nonces are a real decoder-known salt channel. The
   decoder knows the prefix token state before opening each record, and the toy
   round-tripped `200/200` without nonce fields or birth tags. It maintained
   hit/window across six passes (`0.03444`, `0.03533`, `0.03476`, `0.03554`,
   `0.03398`, `0.03295`) but still bloated random 192-bit inputs to `1661.38`
   bits after six passes. State refresh solved freshness better than fixed
   rechunking, but literal carriage still defeated net compression.
21. Sparse-map prefix-state accounting removes the bad literal-token overhead.
   It stores only miss bits, seeds, and an optimistic non-overlap map
   `log2 C(n-(L-1)m,m)` plus the match-count class. It still lost:
   on 512-bit random inputs, `16.950` matches saved `67.800` gross seed-span
   bits, but the map+count cost averaged `94.521` bits, for `538.721`
   charged bits and `-26.721` net. The remaining bill is selected-span
   entropy, not token syntax.
22. Scheduled-slot prefix-state accounting removes the selected-position map by
   using public non-overlapping slots. It nearly breaks even but still loses:
   on 512-bit random inputs, `2.240` slot hits produced `517.828` charged bits
   (`-5.828` net) once the hit-count class is charged. The closed-form
   scheduled-slot ledger `p*d - H(p)` is negative for all tested positive gaps
   `d=L-r`; the hit bitmap is the open/carry channel.
   The parent-summary variant stores a small group summary before child slots
   and salts each child by `(summary, local_slot)`. This is a real
   decoder-known salt and verifies after child decode, but each child has only
   one active parent state. At 14-bit spans, 10-bit seeds, and 1024-bit random
   inputs, summary widths 0, 2, 4, and 6 all lost; the best sampled row was
   summary 0/group 16 at `-8.706` bits, while summary 2/group 16 worsened to
   `-16.630`. Parent summaries are metadata, not extra arbitrary coverage.
23. Scheduled-edge exclusion rules use a public `(pass, slot)` class as a
   decoder-known salt and omit those class bits from the stored local seed. The
   exact toy round-tripped across three public passes, so freshness is real,
   but every omitted class bit halves eligible seed supply. On 1024-bit random
   layers, edge bits 0-4 all lost (`-9.590` to about `-5.466` bits in the
   best sampled row), and the closed form `p*gross - H(p)` stayed negative.
   The schedule is a valid free salt, not a compression subsidy.
24. Seed-length class as nonce uses the record class to select seed length and
   salt the expansion. The decoder knows the class before expanding, and the
   exact toy round-tripped across three public passes. Multiple classes raised
   hit rate (`9/10` reached about `0.092` hit/slot versus `0.064` for `10`
   alone), but fixed class IDs and longer addresses made charged net worse:
   the closed form moved from `-8.729e-02` bits/slot for `10` to
   `-1.358e-01` for `9/10` and stayed negative for all tested class sets.
   Seed length is a valid parser-known salt, but not a free match-rate subsidy.
   Arity-header-known nonce gives the same question a span-length version:
   arity is parsed before expansion and can salt the seed. The exact layered
   toy round-tripped `120/120` and kept finding arity-3/4 records over four
   fixed-universe passes, but visible tokens grew 256 random bits to `546.33`
   bits (`-290.333` final delta), and the lower-bound parse-map ledger lost
   `-15.144` to `-20.058` bits per layer. Closed form stayed negative for
   compressive arities (`a3=-0.13812`, `a4=-0.00867` bits/window). The arity
   header is a real nonce, but it is also the paid parse/open channel.
   The value/count separation variant stores only class histograms, not per-hit
   class IDs. Count-only ledgers look positive (`d4` count net `+0.17417`),
   but the missing assignment entropy flips feasible rows negative (`d4`
   full net `-0.08729`, `d8` `-0.00562`, `d4+d8+d12` `-0.09288`). Positive
   full-net jackpot rows require impossible density, e.g. saving 16 bits with
   hit probability `2^-8`.
25. Grouped scheduled bundles try to amortize the bitmap by accepting only
   all-hit public slot groups. This removes the flattering finite near-miss
   only if the group hit count is silently free; once charged, 4096-bit random
   trials lose `-29.620`, `-6.558`, `-6.399`, and `-6.160` bits for group
   sizes 1-4. The closed form `p^g*g*d - H(p^g)` stays negative: grouping
   thins hit supply by the same exponent that it saves bitmap frequency.
   Bundle-geometry partition selector lets the group shape itself be the
   decoder-known nonce and open/carry template. The exact toy round-tripped
   `160/160` and found shape-specific records across four reserialized passes,
   but visible mode bits grew 512 random bits to `858.62` (`-346.625` final
   delta), and the optimistic enumerative mode-map ledger lost `-23.505` to
   `-28.687` bits per layer. Even the closed all-shape union estimate stayed
   negative (`-0.47256` bits/group). Geometry can salt, but selecting geometry
   is the paid group-scale map.
26. Bucket-directory one-hit hit map stores a public bucket directory and at
   most one local hit per non-empty bucket. It is a middle ground between a
   per-slot bitmap and all-hit groups. The exact toy round-tripped but lost
   for bucket sizes 2, 4, 8, and 16 (`-28.022`, `-25.641`, `-22.442`,
   `-18.260` bits on 4096-bit random layers). The closed form stays negative:
   for group 4, bucket hit probability `0.22752` gives expected one-hit saving
   `0.45505` bits but directory entropy `0.77367` plus a 2-bit local index.
   Coarsening the bitmap buys a local coordinate bill and discards extra hits.
27. Bitmap-free all-or-raw block mode removes mixed open/carry positions
   inside each block. A block compresses only when every scheduled slot hits;
   otherwise it is raw. The exact toy round-tripped, but one mode bit per
   block dominated: 4096-bit random layers lost `-221.580`, `-142.440`,
   `-96.880`, `-73.000`, `-36.000`, and `-18.000` bits for group sizes
   1, 2, 3, 4, 8, and 16. The closed form `p^g*g*d - 1` is negative for all
   tested groups, and a whole-layer all-hit mode has essentially zero random
   hit probability. The hole-run bundle occupancy variant is the clean
   egg-carton check: a 4-chunk bundle leaves three holes that identify
   open/carry if the board remains visible. It round-tripped `120/120`; the
   impossible packed-hole oracle was `+23.800` bits, but visible mode bits were
   `-232.200`, explicit cell occupancy was `-1000.200`, and the tight
   enumerative hole map was `-11.712`. Holes are therefore a valid signal only
   in the representation that pays for the hole pattern.
28. Greedy score-order count-only hit map omits the bitmap and stores only
   seed/literal streams. A public slot order says every matchable chunk must
   be opened; carried literals are valid only when they are outside that slot's
   seed image. The exact toy round-tripped `400/400`, but the decoder still
   saw `17.302` valid maps on average and unique decode only `44.3%` of the
   time. The rule avoided `2.504` bitmap bits but left `2.175` ambiguity bits;
   charged net was `-2.776` bits on a 96-bit block. Structural local validity
   prunes maps but does not derive open/carry for free.
29. Prefix-stop count-free hit map removes both bitmap and per-block hit count
   by opening consecutive matchable slots in a public order until the first
   miss. The exact toy round-tripped `120/120`; it had `2.200` bits of free
   saving and `1.333` ambiguity bits, leaving an apparent `+0.867` bits. But
   the total compressed length is the hidden stop-count/savings class. Charging
   that `5.615`-bit class gives `-4.748` bits. The finite positive row was a
   length-channel artifact, not recursive compression.
30. Checksum-pruned hit-map search omits the hit bitmap and lets the decoder
   enumerate all `C(slots,hits)` ordered seed/literal assignments, keeping
   only those whose block checksum agrees. This is a real nonlocal coupling,
   but a short checksum is ambiguous and a long checksum becomes the bitmap:
   in the 12-slot exact toy, checksum 0 leaves `26.390` survivors on average
   and only `0.410` unique decodes, while checksum 12 reaches `1.000` survivor
   but loses `-12.760` bits on a 96-bit block. The hit count is also a
   channel unless stream lengths expose it and are charged.
31. Tagless value-code open/carry derivation removes the bitmap entirely.
   For each decoder-known state, seed-image chunks get short prefix codewords
   and non-image chunks get long complement codewords, so the decoder derives
   open/carry from the parsed value class. This maintained fresh hits across
   passes and round-tripped exactly, but Kraft conservation moved the bill to
   misses: 512-bit random inputs bloated to `738.14` bits after four passes at
   short length 5, to `756.05` bits at short length 6, and stayed exactly raw
   at short length 8. The ideal one-chunk ledger is minimized at the no-saving
   point where short codewords are as long as raw chunks.
32. Finite-class local grammar bound generalizes visible nonces, seed-length
   classes, tagless value codes, and local lane salts when open/carry is
   decided by a local prefix grammar. Under the optimistic model with disjoint
   seed images and ideal fallback coding, every tested design had expected
   length at least raw. The brute-force sweep's best short-code designs only
   reached `14.00011` expected bits for 14-bit chunks (`-0.00011` save), and
   the tempting local `9/10` seed-length code is invalid because it consumes
   the whole Kraft tree while leaving misses. This is a scoped impossibility
   for local parser-known nonce tricks, not for nonlocal channels or shaped
   sources.
33. BBL random-density surface separates the finite wrong-pass ambiguity ledge
   from arbitrary/random density. High arity makes `c_a(P)` tiny (`arity=5`,
   `P=1,000,000` has `c=2.111` bits), but random scheduled windows still need
   the open/carry hit map. The best sparse row at that setting has no-map
   expected gain `1.476e-02` bits/window but map-priced net `-5.116e-02`;
   a dense 50% layer would require a 63-bit gap whose uniform hit probability
   is only `1.355e-20`. BBL remains a real dense selected-bundle ledge, not a
   random-density solution.
34. Self-dating grammar residues reduce wrong-pass ambiguity, but they also
   lengthen every true target and shrink arbitrary hit supply. In the toy
   sweep at `P=1,000,000`, the best expected net per arbitrary window was only
   `6.018e-05` bits at arity 2 with 6 residue bits.
   The residue/syndrome trilemma makes the conservation explicit. With
   `data=8`, `seed=6`, `chunks=64`, and `P=1,000,000`, raw-filter residue
   pruning at 6 bits lowers wrong-pass survival to about `0.01621`, but
   hit/chunk falls to `0.0000` in the exact sample and the closed ledger is
   `-0.001`. Constraining the expander to valid strings gives wrong-pass
   survival `1.00000`; storing a syndrome restores arbitrary data hit/chunk
   around `0.23` but pays the residue in the record and still has closed
   ledger `-5.294`. Residue bits can prune, repair arbitrary targets, or stay
   unpaid, but not all three.
35. Derived validity from visible seed classes avoids extra residue bits, but
   the same information reappears as seed-supply loss. Best toy row:
   `5.137e-05` expected net bits/window at arity 3 with 6 class bits.
36. Nested referee checks make wrong-pass openings die at recursive internal
   nodes, and the exact toy wrapper round-tripped `5000/5000` arbitrary
   payloads with `21/5000` random wrong streams surviving versus `19.53`
   expected. But the anti-reward-hack ledger splits the result: the best
   fantasy free-validity row was `7.273e-04` expected bits/window, while the
   same row fell to `4.335e-11` when the referee bits were stored in the target
   or derived from seed classes. The best charged row was only `1.274e-07`,
   and it was shallow (`arity=5`, `depth=1`, `check=1`), so nesting itself did
   not create a cheap birth/salt channel.
37. Self-consistent output-derived nonces are stateless: the decoder tries nonce
   values and keeps only expansions whose output hashes back to that nonce.
   But the finite book stayed around one output per seed (`958` to `1057`
   outputs for `1024` seeds across nonce widths 0-6), so nonce bits did not
   multiply arbitrary target coverage.
38. Final-position/egg-carton boards are not rejected by assumption; they now
   have an optimized entropy gate. Shrinking `R` lowers the total final note,
   but the best possible per-survivor pass-label lower bound remains
   `log2(P)`: `P=4` is already break-even against a 2-bit match win, and
   `P=64` is `-4` bits/survivor before slot/order overhead. A universal lane
   board with `R=100`, `P=64`, `Q=P*R` costs `7.385` occupied-cell bits per
   survivor. Histogram/count separation is not free: for `R=32`, `P=4`,
   `H(hist)=9.616` and expected assignment entropy is `54.384`, totaling
   exactly `2.000` bits/survivor.
   The affine-orbit/final-coordinate toy makes the same point mechanically:
   final-coordinate salt is stateless but stale, with hit/chunk near `0.031`
   and closed net `-0.044` for `P=1..32`; birth-coordinate salt refreshes
   supply (`0.6411` hit/chunk at `P=32`) but owes about `log2(P)` phase bits
   or ambiguity, and the tight ledger worsens to `-62.220` bits. Public orbit
   phase reads total motion, not birth.
39. The 50% arbitrary/random finish condition has a counting gate. For `n=128`,
   all outputs of length `<= n/2` cover only about `1.084e-19` of `n`-bit
   inputs, leaving about `63` missing bits per input. Any future candidate must
   locate those bits as paid side information, exceptions, non-injectivity, or
   a distributional restriction.
40. Exception fallback does not evade the 50% gate. Even with optimistic
    n-bit raw exceptions and no per-block tag, the maximum fraction of `n=128`
   inputs that can fit in `<=64` bits is only `1.084e-19`, giving a best
   average saving of about `7.047e-18` bits/input. With a one-bit raw tag, the
   average is effectively `129` bits.
41. Window/placement multiplicity buys coverage only by creating a coordinate.
    In the toy `L=32, r=16` ledger, `45426` trials give 50% hit coverage and
    an apparent free expected gain of `8.000` bits/chunk, but the coordinate is
   `15.471` bits, leaving only `0.264` priced expected bits/chunk. At full
   `65536` trials, the coordinate consumes the entire 16-bit nominal saving.
42. Repeated public-salt compute does not evade the bill by itself. For
    half-size records (`r = L/2`), making half of random spans hit requires
    about `2^(L-r)` trials. The implicit trial coordinate is about `L-r` bits,
    leaving only about `0.529` bits saved per hit after pricing in the toy
    ledger.

The next mutation should not add a bigger generated positive control. It should
look for a context-lane grammar whose nonce changes across passes without
depending on future neighbors, and whose wrong-lane structural failure is much
stronger than the loss in true arbitrary target supply. So far, every tested
lane/check either becomes stored address bits, surviving decode ambiguity,
wrapper bloat, unstable context, output-self-consistency without added supply,
seed-supply loss, or an implicit compute/trial coordinate.

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
