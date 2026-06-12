# Telomere — State-Model Comparison (spec & math only; no tests)

Maintainer's directive, June 2026: "birth pass" claims are meaningless until
the state model is stated. This document defines four designs, answers the
ten questions for each, and fills the comparison table. Every claim here is
algebraic or counting-based; no randomized encode/decode runs were used.

Throughout: σ is the fixed shuffle rule (i → 5·i mod P, exactly invertible,
i → 5⁻¹·i mod P). T = total passes (derivable via stop-at-first-empty, or
13 header bits — never the issue). Reversibility of σ itself is settled and
identical in every design.

---

## Design A — Atomic-entry shuffle (the model all prior analysis used)

1. **State at pass start:** the current item sequence (records + literals),
   count N_t changes whenever bundles form.
2. **Replacement operates on:** windows of adjacent *items*.
3. **Shuffle permutes:** items; modulus = least prime ≥ current item count
   (count changes ⇒ modulus changes per pass).
4. **Bundle atomic next pass?** Yes — a bundle is one item from birth onward.
5. **Decode expands before inverse shuffle:** exactly the records born in
   the pass being reversed (restores last pass's count), then unshuffle.
6. **Birth pass needed?** Yes, for bundles (arity-1 is count-neutral and
   commutes). Algebraic reason: the replace step has two preimages
   ([La][Lb][R*] and [R1][Lc][Ld] both → [R1][R*]); picking wrong changes
   the count fed to every remaining unshuffle.
7. **Inferred or charged:** stride inference over *changing* counts (open
   proof; the hard part is threading cumulative index-shift maps through
   varying moduli), or explicit ≥5 bits/bundle (priced net-negative).
8. **Inverse algebra:** exists only given per-bundle birth; no formula
   without it (two-preimage counterexample above).
9. **Serialized:** final item sequence + header.
10. **Encoder-only state:** none beyond the sequence (that is the appeal —
    and the cost: history lives nowhere, so decode must reconstruct it).

## Design B — Transparent / block-state shuffle (the maintainer's model, formalized)

**Definition.** The state is the original N blocks, N CONSTANT forever.
σ acts on the block sequence with FIXED modulus P (least prime ≥ N), every
pass, including blocks already claimed. A record never becomes a state
object: replacement is *annotation* — a record R born at pass k claims
blocks adjacent in the σᵏ-order, positions q..q+a−1. Claimed blocks keep
shuffling but are no longer searchable (windows = runs of adjacent
unclaimed blocks).

1. **State at pass start:** the N blocks in σ^(t−1)-applied order + a
   coverage map (which blocks are claimed, by which record).
2. **Replacement operates on:** adjacent runs of *unclaimed blocks* in the
   current order.
3. **Shuffle permutes:** the N blocks. Modulus never changes. Total
   permutation after pass t is σᵗ — pure index arithmetic, content-free.
4. **Bundle atomic next pass?** No — transparent. The bundle never exists
   in the state; its blocks remain and keep shuffling.
5. **Decode expands before inverse shuffle:** nothing interleaved. Decode
   is direct placement: every leaf's original position is computed by one
   formula (below); there is no staged unshuffle loop at all.
6. **Birth pass needed?** The *information* k is needed per bundle — but
   the problem changes character completely:
   - A record born (k, q) has child j at final-order slot σ^(T−k)(q+j) and
     original position σ^(−k)(q+j). Placement of children is k-dependent.
   - **Exact metadata bound: ≤ log2(T) bits per bundle** — k ∈ {1..T} is
     the only unknown (q is recovered from the record's first wire slot:
     q = σ^(−(T−k))(f)). Compare Design A, where the unknown is entangled
     with every pass's changing count.
   - Literals need nothing: original position = σ^(−T)(f), T known.
   - Singles need nothing *for placement* (one block, slot = where found).
7. **Inferred or charged:** T-candidate test, fixed arithmetic: for each
   k ∈ {1..T}, compute the a child slots σ^(T−k)(q+j); a candidate k is
   consistent only if all its slots are currently unfilled and mutually
   compatible with every other record's claims. Wrong-k survival per
   candidate falls geometrically in arity (each extra child slot must
   coincidentally land unfilled); residual ambiguity → 1-bit charged
   escapes; global backstop = the header's output hash. **The lemma to
   prove is this escape bound — a fixed-modulus counting problem, far
   smaller than Design A's induction.** Bonus: the same inferred k replays
   the pass-k salt, so bundle salting is decodable for free once k is known.
8. **Inverse algebra (given k):** original_position(child j of R born
   (k,q)) = σ^(−k)(q+j); original_position(literal at final slot f) =
   σ^(−T)(f). Two one-line formulas; the inverse of the entire process.
   Why k is irreducible: for T ≥ 2 there exist wires where two values of k
   both map all children to unfilled slots — the wire alone underdetermines
   placement, so the information must be inferred (cheap) or charged
   (≤ log2 T bits).
9. **Serialized:** walk the final order σ^T: unclaimed slot → literal item;
   slot that is some record's first slot → the record; other claimed
   slots → nothing (filled at decode by the placement formula).
10. **Encoder-only state:** the coverage map and the pass index (both
    reconstructible; nothing hidden in the wire).

**Honest limits of B:**
- **No recursion.** Records are never re-compressed (they are not state
  objects), so the grinding channel — the thing the salted Monte Carlo
  showed compounding without bound in Design A — does not exist inside B.
  B is a one-shot coverage machine: every block claimable once. Its
  ceiling is bounded (≈ avg 2 bits saved per accepted record, once per
  covered span), approached as T → ∞ since the shuffle keeps offering
  fresh pairings.
- **Singles stay bounded.** A single's placement needs no k, but a salted
  single's *expansion key* would — and a lone block offers no positional
  structure to infer k from. Position-keyed dice (key = original position,
  k-free, decoder computes it) are legal but give one deterministic dice
  sequence per block, exhausted at the depth ceiling D*. So in B, singles
  are a bounded opening act; **bundles are the engine** (their k-inference
  carries their salt).

## Design C — Encoder-only search shuffle

1. State: blocks in original order, coverage map.
2. Replacement: original-order adjacent runs only.
3. Shuffle permutes: nothing decodable — only the encoder's search *order*.
4. Bundles: n/a (no wire effect of shuffle).
5. Decode: normal left-to-right; no inverse shuffle exists.
6. Birth pass: not needed.
7. —
8. Inverse: trivial (identity on positions).
9. Serialized: original-order items.
10. Encoder-only: the search schedule.

**Verdict:** decodes trivially and is supply-bound. Each original-order
window has one fixed content; without a decodable per-pass key its dice
are exhausted deterministically (the unsalted Monte Carlo lane: stalls
~13% above original, forever). This row exposes what the shuffle is FOR:
not "movement" — it is the *decodable source of fresh dice*. Salts alone
provide freshness the decoder can't replay; the shuffle provides freshness
the decoder can reconstruct from arithmetic. That is the design's actual
function, stated plainly for the first time.

## Design D — Strict layer stack

1. State: the entire previous emitted bitstream, re-blocked as a new file.
2. Replacement: spans of the new blocking.
3. Shuffle: optional per layer (each layer is self-contained).
4. Bundles: layer-local; never cross a layer boundary.
5. Decode: layer by layer, outermost first; no cross-layer epochs at all.
6. Birth pass: not needed (the layer boundary IS the epoch, paid for in
   carriage).
7. — (charged in carriage, not in inference)
8. Inverse: each layer is a closed codec; composition of inverses.
9. Serialized: top layer + header chain.
10. Encoder-only: nothing.

**Verdict:** decodable today, recursion included — but every layer pays
carriage (run headers around each record island). Prior priced lanes of
this family ranged from net-negative (explicit-flag rechunk, −24.7%/pass)
to marginal; viable only where hit density is already high. Costly, as the
maintainer's table predicted.

---

## The table

| design | shuffled unit | bundle atomic next pass? | decode order | birth pass needed? | metadata | viable? |
| --- | --- | ---: | --- | ---: | ---: | --- |
| A. atomic-entry shuffle | current records/items | yes | unshuffle ↔ expand current-pass records, staged | yes (bundles) | stride/epoch over changing counts (open, hard) or ≥5 b/bundle (negative) | pending — hard proof |
| B. transparent block-state shuffle | the N original blocks (N constant) | no — transparent | direct placement by formula; no staged loop | k needed per bundle, ≤ log2 T bits; placement-free for singles/literals | **zero if T-candidate test proven (easy lemma); same k replays bundle salt** | **pending — easy lemma; bounded ceiling (no recursion)** |
| C. encoder-only search shuffle | search view only | n/a | normal decode | no | zero | no — supply-bound (stalls at refund) |
| D. strict layer stack | whole previous bitstream | layer-local | layer by layer | no (layer boundary = epoch, charged) | high carriage | likely costly (matches priced lanes) |
| **B + D synthesis** | blocks within a layer; layers stacked | transparent in-layer | placement formula in-layer; layers outermost-first | k in-layer only (B's easy lemma) | carriage per layer + zero epoch bits | **most promising — to price** |

## UPDATE (June 2026): Design B proven by construction

After this comparison was written, Design B was implemented end to end:
`model_analysis/proof_kernel/v1_roundtrip_proof.py` — 36/36 exact
multi-pass round trips with salted bundles, slot-keyed singles, T derived
by trial, birth passes inferred by the T-candidate test, ambiguity forks
settled by the header hash, decoder inputs = wire + N + B + hash only.
Design B is now the NORMATIVE V1 state model (`SPEC_V1.md` §3). The
B-lemma (analytic escape bound at scale) and the B+D carriage pricing
remain the two open analytic items (Q1, Q2).

## Where this leaves the program

1. The maintainer's objection stands as stated: "birth pass is required"
   was a Design-A theorem being presented as universal. In Design B the
   required information shrinks to a bounded, fixed-arithmetic inference
   with the salt replay thrown in free.
2. Design B alone is bounded (no grinding). Design D alone is decodable
   recursion at high carriage. **B stacked inside D** buys recursion back
   while keeping zero epoch metadata: run B to coverage saturation, emit,
   re-file, repeat — carriage charged at each re-file, priced by the
   existing run-header arithmetic.
3. The two proofs now in queue, both pencil-and-paper scale:
   - **B-lemma (escape bound):** wrong-k survival rate of the T-candidate
     occupancy test as a function of arity and fill fraction; charged
     1-bit escapes for survivors; show expected escape cost ≪ 2-bit
     average win.
   - **B+D carriage ledger:** per-layer cost of re-filing vs per-layer
     coverage earnings; break-even hit density per layer.

No further randomized encode/decode tests until both are written. The
prior Design-A artifacts (sweeps, stride induction task) are parked, not
deleted: if the B-lemma somehow fails, A's stride induction is the
fallback lane.
