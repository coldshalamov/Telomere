# Birth-Channel Hunt — Final Verdict (June 2026)

*Two adversarial multi-agent phases (16 lane-attacks + a 3-skeptic panel),
hypothesis-first, math/exact-counting over hash-and-pray, every positive claim
forced through the counting gate. Load-bearing artifacts independently re-run
by the research lead. This file is the bankable result.*

## Bottom line

**The free, content-blind, *unbounded* birth-pass channel does not exist.**
This is a **sharp impossibility** hinging on one named assumption — the
**uniform hash law** — with a **quantified finite max-free-reach K**. No
working unbounded configuration was found and none is reportable. The bankable
deliverable is the conservation theorem + the finite K + a correction to the
repo's own decode headline.

**The conservation law (the gate every lane walked through):** a birth channel
that is *free* AND *content-blind* AND *unbounded* is a pigeonhole violation
(it would convey uniform-hash birth outcomes — incompressible — for free,
mapping 2^n inputs into fewer outputs). Every lane passed this gate by naming
the **finite resource** that bounds it. None found a free unbounded channel.

| Question | Verdict | Bill paid in (currency) | Evidence |
| --- | --- | --- | --- |
| Singles birth pass (the prize) | **impossible** (unbounded) | stored-bits: checksum → N·log2(T) | proven |
| Bundle birth epoch | **impossible** (unbounded); finite knee K=2^E≈655 | stored-bits past the knee | proven-by-construction |
| Keystone relax (biased hash) | **conserved** | match-supply, 1 bit per bit | proven-by-math |
| Max explosion budget E | **impossible** to close | stored-bits (residual log2 T − E) | proven-by-math* |
| Recursion / layer-stacking | **conserved** | wrap/carriage (per-layer re-block) | proven-by-math |

*the length-pinned E *values* are partly conjecture; the structural facts
(E=0 on singles, c_mean>0 ∀T≥2) are proven. The repo's exact 2.5 derivation was
not located — no reproduction claim is made.

---

## 1. Singles (arity-1) — the cleanest wall, sharper after Phase 2

The channel sustained compounding actually needs.

- **`I(birth-pass ; position) = 0`** (4 independent lanes, proven-by-math). A
  length-preserving single occupies its slot the whole run; its position at
  pass j is σ^j(x) for all j, independent of birth pass t. The decoder already
  owns the entire trajectory (x = σ^−T(p_final)). Birth pass is a *content*
  event (when the lottery first hit the slot), logically independent of the
  trajectory — two files differing only in t have identical trajectories. No
  position function (orbit phase, CRT residue, Zeckendorf digits, parity/sign)
  can carry it.
- **Trial-decode ambiguity is exactly `S = T^R`** (Lane B, real-SHA DFS,
  re-run by lead: T=100, R=3 → 1,000,000 survivors, integer-exact). A single
  is 1→1 and expands to a valid literal at *any* salt, so the explosion check
  never prunes it; the only freedom is which of T reverse walks it opens on.
  Deterministic decode needs an `R·log2(T)`-bit referee = the checksum; scaling
  to N singles forces the checksum to grow to `N·log2(T)` = the birth bill.
- **No explosion subsidy for singles: `E = 0` exactly** (Phase 2 budget lane,
  proven-by-math; consistent with Lane B's q=1). The ~2.5-bit explosion check
  is *length-pinned* — it needs a known target span. Arity-1 is one
  length-unconstrained item (SPEC §2.3), so a wrong salt has nothing to
  violate. **Phase 1's "K≈5–6 for singles" was an artifact of crediting
  singles with the bundle/length-pinned 2.5 bits — withdrawn.** The honest
  singles object is the joint ceiling `N·log2(T) ≤ ~64` (≈11 records at T=64),
  collapsing to T=1 as N→∞. **Both the position channel and the structural
  channel are empty.**

**Currency: stored-bits.**

## 2. Bundles (arity ≥ 2) — finite knee, not a free channel; 3/3 skeptics confirmed

The only structurally-distinct un-refuted thread (real explosion check q<1,
and a k-slot span — but see the lock below).

- **Mechanism (a), not (b)** (proven-by-construction, real SHA on J3D1 Lotus):
  the explosion check only **lowers the base** of an exponential survivor count
  `base = 1 + (G−1)·q_bundle`, with `G ≈ T` (content-blind, measured) and
  `q_bundle = 100/65536 = 0.001526` (E = 9.36 bits). It does **not** pin the
  epoch to O(1). Survivors `S = base^R` are exponential in R.
- **Free-reach knee `K = 1/q = 2^E ≈ 655` passes** (arity-2). Below K base≈1
  (epoch near-free *in expectation*); past K the per-bundle residual
  `log2(base) → log2(T) − E` grows without bound, paid in **stored-bits**. This
  reconciles the refuted "5.66 free passes" folklore as the E=2.5 special case
  of the law **K = 2^E**.
- **Higher arity moves the knee, never the slope:** E = 9.36 / 12.59 / 14.97 /
  18.20 bits at arity 2/3/4/5 → K = 655 / 6186 / 32198 / 302029 passes. Killing
  the slope needs E growing *with T*, impossible for a fixed grammar.
- **The k-equations-vs-2-unknowns hope is false** (Skeptic 1, conceptual lock):
  bundling **shrinks the wire** — encode emits one item per bundle
  (`skip.update(slots[1:])`); the other k−1 slots become *holes* that emit
  nothing. The decoder gets **one** observation per bundle, not k. The hole
  positions *are* the birth information (Skeptic 2 proved this: handing the
  decoder the true hole set manufactured a fake O(1) pin — a packed wire
  physically cannot carry holes).

**Skeptic panel (3 independent adversarial passes): all confirmed; none broke
it.** Self-caught false-positives (Skeptic-2's injected-hole "channel",
Skeptic-3's slot-0 identity) strengthen rather than weaken the verdict.

**Currency: stored-bits past the knee.**

## 3. The repo headline correction — the user's instinct, vindicated

The repo states *"Multi-pass decode with zero stored metadata is PROVEN BY
CONSTRUCTION"* (`v1_roundtrip_proof.py`, 36/36) and treats bundle epochs as
*solved* (affine-stride fingerprint). Forensic dissection (proven-by-math):

- **TRUE as a storage statement:** bundle birth epochs genuinely cost **zero
  stored bits** — bundling shrinks the wire; coverage is positional, no PCTB
  occupancy tax.
- **FALSE as a scaling statement:** decode re-derives child placement via
  `sig_pow(bwd, q+j, k−1)`, which *needs* the epoch k, **derived by a DFS, not
  read from structure.** The candidate filter (lines 172–183) is **content-
  blind** (321 distinct-content wires → byte-identical candidate sets; all
  epochs 1..T survive for most bundles), so it provably cannot convey a
  content-determined epoch — 100% of disambiguation falls on the fixed 256-bit
  header hash. Forks at the correct epoch: **171 → 3388 → 6874** at T=5,6,7
  (N=16), blowing the native `fork_budget=128` by **54× at T=7**. Every "None"
  is **budget-killed, not structural** (all recover at budget=20000). The 36/36
  sits at `N·c_mean = 3.86 << 64` — deep in the free region.

**So 36/36 proves the mechanics are sound *where birth is already cheap*
(T≤5); it says nothing about the wall.** The maintainer's suspicion — *bundling
is really the problem* — is vindicated: not as the open lane, but because the
claimed bundle *solution* was the hidden overclaim. Suggested re-scope of the
headline: *"decode mechanics proven below the wall (T≤5); bundle birth-epoch
storage is genuinely zero bits; scaling past K≈6 is paid in compute/stored-
bits (DFS forks ~×2/pass)."*

## 4. Keystone (biased / structured hash) — the one relaxation, also conserved

The single keystone the whole wall hinges on is the **uniform hash law** — the
only premise whose relaxation correlates birth pass with something already on
the wire (the stored seed field). Attacked directly (proven-by-math, exact
enumeration):

- Free seed→pass decode needs disjoint per-pass eligible seed sets; under the
  uniform hash law supply ∝ count, so disjointness forces `Σ|S_t| ≤ |S_all|`:
  T passes net **one** unrestricted pass = **exactly 1 supply-bit per conveyed
  birth-bit**, value-independent.
- Count and value are **co-located** (E[win|hit]=2.00, CV≈0.70) — no value
  spread for a class-decodable partition to exploit; the "jackpot" class
  isolates ~0 supply and conveys ~0 bits.
- The soft/non-disjoint escape is closed by the counting-gate converse:
  `supply ≥ I(L;t)` for *every* coupling. **Total bill = log2(T), conserved at
  every bias level.**

**Currency: match-supply.** This is genuine double-duty reuse of the on-wire
seed field — but fully conserved.

## 5. Recursion — does not net-compress content-blind

Re-running output as a fresh file (the legal recursion channel) with birth
*free* within K (proven-by-math):

- **Per-layer net is negative:** −0.352 b/bit (~K draws) / −0.371 b/bit (~1
  draw). The free birth channel removes the log2(T) tax but **not** the
  wrap/carriage tax (literal re-marking on the ~98% unclaimed windows).
- **Recursion does not change the sign** (content-blindness → every layer same
  base rate → layer-invariant → geometric sum collapses to single-layer sign).
  Under kept-if-shrinks, 0/64 layers kept; bounded raw+ε, no catastrophic
  bloat.
- **Flip density = 47.5× base = `p_needed ≈ 0.185 ≈ p* = 0.193`**,
  independently reproducing the repo solver's 48× for B8/canonical/a2 from a
  birth-*free* starting point. That density is content-aware (GOLDEN §2),
  outside the content-blind program.

**Currency: wrap/carriage.** Recursion converts the unbounded-T birth tax
(stored-bits) into a per-layer re-blocking tax; at base rate carriage ≥ the tax
it saves. Same wall, different currency.

---

## The frontier (if anyone wants to keep pushing)

The entire wall rests on **one brick: the uniform hash law.** The keystone lane
(§4) shows that relaxing it via seed-coupling is conserved (match-supply). The
*only* un-eliminated shape is a hash whose bias couples birth pass to the
stored seed at **sub-1× supply loss per bit** — and §4 proved that requires
value/count to *not* be co-located, which they are (CV≈0.70). To overturn the
wall one must exhibit a compressive-seed population where value and count
*separate* (so a class-decodable partition sorts high-value low-count seeds
without losing proportional supply). No such population exists at the Golden
Config. That is the precise, minimal target for any future attempt — the same
discipline by which the maintainer overturned the 2-bits-per-block cap.

## What is NOT claimed

No working unbounded config. No net compression of content-blind data (that
remains pigeonhole-forbidden, as the repo already holds). The four self-caught
false-positives across the run (bundleTest's "S=1 below knee", Skeptic-2's
injected-hole "channel", Skeptic-3's slot-0 identity, biasedHash's inverted
formula) are evidence the conclusions survived genuine adversarial pressure,
not affirmation.

## Artifacts

`model_analysis/birth_channel_research/` — `BRIEF.md` (the research contract),
`findings/` (per-lane working: A–H, P2-forensics, P2-biased-hash,
P2-explosion-budget, P2-recursion-ledger, P2-bundle, S2-bundle-refutation,
P3-skeptic3-arity-refutation), and runnable toys (`B-ambiguity-bound_survivor_count.py`,
`E-explosion-amp_ambiguity_ledger.py`, `H-impossibility_residual_ledger.py`,
`P2-bundle_survivor.py`, `SKEPTIC1_G_scale_probe.py`, `S2-joint_consistency_dfs.py`,
`P2-biased-hash_coupling_ledger.py`, `P2-recursion-ledger.py`). Singles wall:
`A/C/D/G-*.py`. PCTB position-tax dead end: `../proof_kernel/pctb_ledger.py`.
