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

## 2026-06-17 Total-Cover addendum

The later Total-Cover branch removes the birth-pass channel by invariant:
every pass fully rewrites the layer, every output unit is a record, and every
record opens during decode. That is a real improvement over the salted
open/carry branch. It does **not** escape the uniform-source conservation law;
the missing bill moves to the paid witness stream `[arity][seed witness]`.

The first honest high-arity paid witness improvement was a public factored
arity+width-delta stream with remaining-atom context:

```text
B=4, K=128, D=512
gain = -0.0313 bits/input atom
missing = 3.518 bits/selected record
```

Later H7/H9/H11 rows improved the miss but did not cross. This row remains the
useful proof that high arity can make the loss near-flat by amortization, not a
positive crossover. See `findings/H2-total-cover-counting-bound.md` and
`H2-uniform_counting_boundary.py`.

## 2026-06-17 finite-K sparse bundle residue addendum

The best remaining sparse salted branch was length-pinned bundles with finite
structural pruning. New H3/H4 ledgers close the tempting residue false positive:

```text
H3 marker-residue charge:
  best charged row = -1.51661 bits/input atom

H4 ideal cover-layout charge:
  best layout-only row = -0.0000175885 bits/input atom
```

H4 is intentionally generous: it keeps H3's marker-derived hit/pruning model
but replaces per-uncovered-literal markers with the minimum enumerative interval
cover cost `log2 C(N-(a-1)m,m)`. Even that upper bound does not cross positive.
Removing markers from the target raises hit density, but then the structural
wrong-pass rejection `E` must also be recomputed; borrowing marker-derived `E`
while matching raw atoms spends the same parse bits twice. See
`findings/H3-H4-bundle-residue-ledger.md`,
`H3-bundle_finite_k_ledger.py`, and `H4-cover_layout_entropy.py`.

## 2026-06-17 high-arity Total-Cover witness split addendum

New H5/H6 ledgers split the remaining high-arity Total-Cover deficit. At the
live target `B=4,K=128,D=512`, the bottleneck is no longer birth, carry, cover
layout, or mostly arity syntax. It is the seed width/slack channel:

```text
H5 current public factored split:
  paid gain   = -0.067796 bits/input atom
  free_delta  = +0.008780

H6 exact suffix partition, alpha=0.02:
  paid gain   = -0.040003 bits/input atom
  free_delta  = +0.006048
```

H6 tests a concrete better witness language:
`P(arity | exact remaining atoms)` and
`P(delta | exact remaining atoms, exact arity)`. It improves the shape but does
not cross. The positive `free_delta` row is only a lower-bound diagnostic: it
would be a hidden channel unless a new decoder-derived invariant determines
payload width/slack without transmitting roughly `4-5` bits per selected
record. See `findings/H5-H6-total-cover-witness-split.md`,
`H5-total_cover_split_ledger.py`, and `H6-total_cover_suffix_partition.py`.

## 2026-06-17 parametric delta-law addendum

H7 tested whether the width/slack bill was partly an H6 sparse-table artifact.
The best paid mode so far is an analytic public raw first-hit delta law:

```text
B=4, K=128, D=512
mode = raw first-hit delta law + public suffix arity model
paid gain = -0.011929 bits/input atom
missing = 1.357 bits/selected record
delta cost = 2.407 bits/selected record
```

This is the closest paid Total-Cover miss in the H5-H7 line. It still does not
cross. The remaining constructive target is now precise: save about `1.36`
more bits/selected record with a public selected-delta residual law, while
preserving rank and arity costs and without file-specific counts or hidden
metadata. See `findings/H7-parametric-delta-law.md` and
`H7-total_cover_parametric_delta.py`.

## 2026-06-17 selected-delta and fixed-width addendum

H8/H9 tested the two most obvious next moves after H7:

```text
H8 objective-tuned beta:
  train-selected beta overfits; held-out beta 0/raw remains best
  narrow run train-selected beta 0.200 -> -0.016322 bits/input atom

H9 canonical fixed slack:
  width_bits = min(D, arity*B - slack)
  stronger run slack 0 -> -0.012314 bits/input atom
```

Fixed slack is honest and stateless because width is decoder-derived, and H9
charges only the `2^W` seeds that `W` bits can actually name. It does not cross:
the saved delta stream is returned through fixed-width padding and lost match
supply. H7's raw first-hit delta law remains the best stable paid row, with H9
slack 0 essentially tied but slightly worse. See
`findings/H8-H9-selected-delta-and-fixed-width.md`,
`H8-total_cover_objective_beta.py`, and `H9-total_cover_fixed_slack.py`.

## 2026-06-17 monotone tail-schedule addendum

H10 tested the richer canonical-width schedule:

```text
slack(remaining) = tail_slack if remaining <= tail_atoms else body_slack
width_bits = min(D, arity*B - slack(remaining))
```

This remains stateless because `remaining` is decoder-derived while reading
arities. It does not cross:

```text
broad grid:
  train-selected body2_tail1_at64 -> -0.037878 bits/input atom
  best held-out diagnostic body0_tail0_at64 -> -0.023648

narrow grid:
  train-selected body1_tail0_at64 -> -0.027325 bits/input atom
  best held-out diagnostic body0_tail0_at64 -> -0.016794
```

Body-stricter schedules overfit training and lose held-out. This closes the
simple monotone fixed-width tail schedule. See
`findings/H10-tail-schedule-fixed-width.md` and
`H10-total_cover_tail_schedule.py`.

## 2026-06-17 selected-order-statistic delta addendum

H11 tested the last low-dimensional public selected-delta idea from the H10
review: price payload width as the minimum of `m_eff` raw first-hit draws,
conditioned on that selected minimum fitting the frontier `D`.

```text
P_sel(W=w | min(W_1..W_m) <= D)
  = (S_raw(w-1)^m - S_raw(w)^m) / (1 - S_raw(D)^m)
```

The conditioning matters. The model is not allowed to assume that every hidden
alternative was already `D`-legal.

Corrected constant-law run:

```text
B=4, K=128, D=512, train/eval=24/16
train-selected m16 -> -0.017810 bits/input atom
best held-out diagnostic m8 -> -0.014353 bits/input atom
```

The diagnostic `m8` law was then frozen and checked on an independent seed:

```text
H11 frozen m8, seed 9001 -> -0.017956 bits/input atom
same-seed H7 raw         -> -0.017439 bits/input atom
same-seed H9 slack 0     -> -0.013061 bits/input atom
```

So the effective-choice-count law does not beat the current paid frontier. It
is useful evidence, not a solution. See
`findings/H11-selected-order-stat-delta.md` and
`H11-total_cover_order_stat_delta.py`.

## 2026-06-17 neutral-fertility capacity addendum

H12 tested the most concrete recursive-fertility channel: neutral witness
multiplicity. If a record has `M` same-width seeds that all reproduce the same
target span, the encoder can choose among them without changing the stateless
record shape:

```text
[arity][seed witness]
```

Under the uniform law:

```text
M ~ Poisson(lambda=2^(W-L)) conditioned on M>=1
neutral capacity = E[log2(M) | M>=1]
```

Those neutral bits are not current compression. They are only an optimistic
future-fertility capacity, and one neutral bit can save at most one future bit
in expectation without an unpriced channel.

The stronger bounded H12 check stayed negative even under perfect one-for-one
future credit:

```text
B=4, K=128, D=512, train/eval=24/16
best row: slack -8
actual gain = -0.050155 bits/input atom
neutral capacity = 3.819 bits/record
perfect-credit gain = -0.008196 bits/input atom
residual = 0.746 bits/record
```

So simple neutral multiplicity is real but too small; buying more neutral
choice by bloating witnesses gives back roughly the same bits. See
`findings/H12-neutral-fertility-capacity.md` and
`H12-neutral_fertility_capacity.py`.

## 2026-06-17 joint selected-cover partition addendum

H13 tested a normalized semi-Markov code over the whole selected cover shape:

```text
shape = [(arity_1, width_1), ..., (arity_m, width_m)]
paid_bits = sum(width_j) + log2 Z(N) - sum(log2 psi_j)
```

The exact seed residual remains paid as `width` bits per selected record. The
tested public potential was:

```text
log2 psi = log2 P_raw(width | arity*B, width<=D)
         + beta * (arity*B - width)
         + record_bias
```

The H13 audit found and fixed a shared sampled-width issue in
`total_cover_lotus_crossover.py`: exact Lotus/J3D1 payload width must be
computed as `ceil(log2(rank+3))-1`. The old `ceil(log2(rank)-1)` approximation
undercounted bucket boundaries such as rank `2`. Future sampled-width rows are
stricter; older rows that used sampled `lotus_payload_width` should be treated
as optimistic unless rerun.

Post-fix H13 result:

```text
B=4, K=128, D=512, N=128, train/eval=24/16
train-selected beta=0.5, record_bias=-10
gain = -0.013941 bits/input atom
missing = 1.586 bits/record

same-seed H7 raw     = -0.012528 bits/input atom
same-seed H9 slack 0 = -0.026809 bits/input atom
```

So raw/tilted whole-cover partition coding returns to the H7 near-miss zone
but does not cross and does not beat H7. See
`findings/H13-joint-selected-cover-partition.md` and
`H13-joint_selected_cover_partition.py`.

## 2026-06-17 public CRF cover-partition addendum

H14 tested the next joint-cover refinement: a small trained public CRF over
selected cover features. The model is still stateless if the weights and
hyperparameters are frozen public profile constants:

```text
log2 psi = log2 P_raw(width | arity*B, width<=D)
         + beta * (arity*B - width)
         + record_bias
         + feature weights

paid_bits = sum(width_j) + log2 Z(N) - sum(log2 psi_j)
```

Features were arity bucket, delta bucket, remaining-atoms bucket, and
arity+delta pair. Weights were trained on independent uniform-law samples using
forward/backward expected feature counts.

The first tiny smoke was positive but train-negative, and stronger checks
removed it:

```text
N=64, train/eval=16/8
gain = -0.019572 bits/input atom
missing = 1.253 bits/record

N=128, train/eval=8/4
gain = -0.015478 bits/input atom
missing = 1.981 bits/record
```

The CRF audit confirmed the forward/backward math for the toy and warned that
profile/hyperparameter selection after seeing eval would be metadata. H14 does
not beat H13/H7 and does not cross. See
`findings/H14-public-crf-cover-partition.md` and
`H14-public_crf_cover_partition.py`.

## 2026-06-17 recursive counting converse addendum

H15 formalized the recursive best-of-pass wall. A stateless recursive
Total-Cover encoder may internally try many passes, profiles, salts, schedules,
or high-arity covers. Once the final representation contains every
decoder-needed selector/header bit, the whole process is one public lossless
code.

For uniform `n`-bit inputs:

```text
Pr[L(X) <= n - s] <= 2^-s
E[L(X)] >= n
Pr[L(X) <= (1-epsilon)n] <= 2^(-epsilon*n)
```

An unpaid best-of-`P` selector can appear to buy at most `log2(P)` bits. Paying
the pass/profile selector restores the ordinary bound. Example:

```text
n=1024, P=65536, target saving s=32
free selector bound ~= 1.5e-5
paid selector bits = 16
paid net saving = 48
paid bound ~= 3.55e-15
```

This does not prove Telomere impossible. It proves the narrower recursive hope
is not an all-data content-blind escape. Uniform/content-blind recursive
compression maintained over arbitrary passes on roughly all data is
counting-forbidden after every underivable choice is either public-fixed or
transmitted. See `findings/H15-recursive-counting-converse.md` and
`H15-recursive_counting_converse.py`.

## 2026-06-17 prior escape ledger addendum

H16 priced the only remaining escape hatch: changing the source model with a
public non-uniform interpreter or source-shaped seed universe.

If a code saves `s` bits on a set `A_s`, then uniform mass satisfies:

```text
U(A_s) <= 2^-s
```

If a source prior `Q` gives that set mass `c`, then:

```text
Q(A_s)/U(A_s) >= c * 2^s
n - H(Q) >= d2(c || 2^-s)
```

Representative result:

```text
n=1024, s=128, c=0.90
uniform max coverage = 2.94e-39
average likelihood-ratio lift = 3.06e38
minimum entropy deficit = 114.731 bits
```

So a public interpreter can be a valid source-shaped compression mechanism only
by bringing a real prior. It is not content-blind roughly-all-data compression.
See `findings/H16-prior-escape-ledger.md` and
`H16-prior_escape_ledger.py`.

## 2026-06-17 original-goal audit addendum

H17 audits the active recursive/stateless goal against the accumulated evidence.
It separates the solved mechanic from the forbidden claim:

```text
stateless decode problem: solved mechanically by Total-Cover
paid witness problem: tested deeply, nearest miss still negative
recursive all-data content-blind goal: impossible by counting
```

The conclusion is conditional, not global. It assumes a fixed public codec,
exact lossless reconstruction, stateless/unique decode from the final stream
and fixed header, and full payment for any selector, profile, pass count,
checksum, table, or adaptive prior the decoder needs. Under those assumptions,
"roughly all data" means the uniform-source law, and H15/H2 apply.

So the original goal is blocked under its stated premises. Telomere work can
continue only by changing a premise or finding a concrete flaw in the counting
assumptions: source-shaped public interpreter, minority-win objective,
dense-class target, practical hybrid, or another explicitly priced mechanism.
See `findings/H17-original-goal-audit.md`.

## 2026-06-17 escape-lane continuation addendum

After the original-goal objection, two adjacent lanes were reopened instead of
treating H17 as the end of all Telomere-shaped research.

H18 quantifies the neutral-fertility target from H12:

```text
best H12 row crosses if future saved bits per neutral bit gamma > 1.195
at gamma = 1.2, gain = +0.000196 bits/input atom
```

Under uniform data, `gamma > 1` is an unpaid information amplifier. As a
premise-shift target, it is precise: a public developmental source needs only
about 20% pleiotropic leverage beyond one-for-one neutral credit.

H19 implements an exact neutral-ecology toy where one stored seed/genotype
publicly derives both current phenotype and future substrate. It crosses for
the ecology-generated source whenever `current_bits + future_bits > seed_bits`,
while uniform arbitrary pairs are covered only on the reachable subset. That is
a valid source-shaped/developmental lane, not a uniform all-data solution.

H20 records the legal collective-witness alternative: arithmetic-code the
decoded layer under the public distribution induced by all cover objects. This
can harvest duplicate-cover entropy, but the uniform average remains bounded by
`N*B + KL(U||Q)`. The next finite kernel is an exact `N<=12`
cover-equivalence DP.

H21 reopens the user's positional/decode-geometry ideas. A per-pass ready
boundary can be extremely cheap when it is truly sufficient: for `N=1,000,000`
and `r=0.10`, the boundary is only `0.000199` bits per opened record. But if
the encoder selected arbitrary sparse hit positions and then compacted them to
the front, the boundary hides a `4.689661` bits/record subset layout. A
deterministic ready lane avoids the subset map, but spends about `3.321928`
match-supply bits per record at `r=0.10`. The surviving target is therefore a
phase-lane Total-Cover hybrid whose ready positions are public, not a
stable-partition of arbitrary content hits.

H22 tested that phase-lane hybrid as an optimistic sparse-bundle ledger. It
replaces H4's arbitrary cover layout with a public active lane, charges
`q*log2(1/q)` match-supply loss plus one boundary, and assumes every lane slot
opens so no intra-lane bitmap remains. The best default-grid row still misses:

```text
arity=5, passes=64
H4 layout-only gain = -0.0000175885 bits/input atom
phase-lane gain = -0.0000361442 bits/input atom
```

So public positional readiness is a valid decoder geometry, but by itself it
does not flip the sparse finite-K bundle branch. It removes a map only by
spending comparable match supply.

H23 audited order-independent final-board decode. Records can open in any
computational order if each one has a public board slot and children are placed
by a public permutation such as CRT/affine/Feistel/prime-walk. That proves the
mechanical possibility of out-of-order stateless placement, but not free
coordinates. A coordinate-free bag adds about `log2(m!)` order entropy; a
seed-derived coordinate costs about `log2 N` extra match bits; sparse
compaction still hides `log2 C(N,m)`. Public final-board geometry therefore
collapses back to H22's lane-supply ledger for compression accounting.

H24 tested the stronger all-open active-lane variant. The arity-sum boundary is
derivable: the decoder reads active-lane records until cumulative arity equals
the public lane atom count. That is a lawful stateless geometry. It is not a
compression improvement over plain Total-Cover. A smoke run showed the old
optimistic arithmetic stream can appear positive on small lanes, but the
stricter paid-count stream is strongly negative:

```text
paid_iid_counts_lotus_payload, lanes=1 -> -3.218999 bits/input atom
paid_iid_counts_lotus_payload, lanes=4 -> -4.737202 bits/input atom
```

Plain Total-Cover can simulate a public lane while also seeing cross-lane
windows, so active lanes should be kept as a decode/salt scheduling invariant,
not as a standalone compression source.

H25 priced the global checksum/referee idea. A checksum can select one reading
out of a finite candidate set, which explains why small trial-decode demos can
work. If each record leaves `M` candidate readings after structural pruning,
then `R` records leave `M^R` joint readings and a referee needs:

```text
C >= R * log2(M) + safety
```

For singles, `M=T`, so the bill is exactly `log2(T)` per record. For
bundle-like structural pruning with `E=9.36` and `T=64`, the per-record bill is
only `0.132` bits and a 64-bit checksum with 32 safety bits covers about `242`
records. But at `1000` records, even that row has `log2 expected false accepts
~= 68`; at `T=65536`, it covers only about `4.8` records. So global referee
bits are real finite help, not an arbitrary-pass asymptotic channel.

H26 isolates the user's latest relative-position idea into the missing
inequality. The best lawful mechanism is a public active lane or final-board
schedule: the decoder knows which slots open, derives the salt from
`pass/lane/position`, reads records until a public arity sum or boundary, and
places children in public coordinates. That is clean stateless decode geometry.
It fails only if "ready" means arbitrary content-selected hits compacted to the
front; then the one boundary hides `log2 C(N,m)`. For `N=1,000,000` and
`r=0.10`, the true comparison is:

```text
boundary/open       = 0.000199 bits
hidden subset/open  = 4.689956 bits
public lane loss    = 3.321928 supply bits
```

So the position trick can remove the hidden bitmap by making readiness public,
but the public lane spends `log2(1/r)` match-supply bits. The constructive
target is now precise: exhibit a decoder-visible class, lane, or grammar whose
selected records are more compressive than average by more than the supply
fraction it removes. At `T=64` states, a uniform class needs `>4` extra value
bits per selected record beyond the rough 2-bit gross match; at `r=0.10`, it
needs `>1.321928` extra value bits per opened record. This is the biology-like
opening if any exists: a public developmental/fertility field where value and
count separate.

H27 prices orderless/confluent decode. Opening records in any computational
order is free only when every child destination is a public function of wire
slot, phase/lane, and child index. If decode instead produces a bag and sorts
later, arbitrary output order costs:

```text
log2(m!) / m ~= log2(m) - log2(e)
```

At `m=1,000,000`, that is `18.488885` bits/record for mostly distinct records.
Even value collisions only reduce it to almost the atom entropy: uniform 4-bit
atoms still carry `3.999863` order bits/atom, and uniform 8-bit atoms carry
`7.998145`. Seed-derived sort keys pay the same bill as match-supply because
random keys have the target order with probability `1/m!`. So orderless decode
is useful mechanics, not a compression source.

H28 turns the value/count opening into a falsifiable fertility-class target. If
a public class has fraction `f`, the supply loss is `log2(1/f)`. Under uniform
hash, public class membership is independent of target equality and selected
value, so `E[value | class] - E[value] = 0`. The exact breakthrough criterion
is:

```text
E[selected gain | class] - E[selected gain] > log2(1/f)
```

For `f=0.10`, the class needs `>3.321928` extra value bits just to beat supply
loss. For `f=1/64`, it needs `>6` bits. Neutral same-cost seed choice has the
same conservation form: it beats the capacity bound only if future value per
neutral bit has `gamma > 1`. This is the live biology-shaped target: public
developmental/fertility classes whose random/uniform controls stay negative,
but whose source-shaped value lift exceeds count loss.

H29 implements the exact H20 cover-equivalence DP. Instead of encoding one
selected cover, define:

```text
Q(x) = sum_{covers c expanding to x} 2^-L(c)
```

and arithmetic-code the decoded layer under public `Q`. This is lawful and
stateless: the decoder does not need selected arities, seeds, or ranks. The
default exact tiny run (`N=12,B=1,K=4,D=8`) covered all layers and saved
`7.210305` bits versus the best local selected cover on average, proving
duplicate-cover entropy is real. But the collective code still averaged
`26.245017` bits for a 12-bit raw layer, and the raw escape mixture chose
`alpha=0`. Denser checks (`D=10`, `N=10,D=12`) moved the number down but stayed
well above raw. The expected uniform edge row explains why: `Q` is a public
subprobability/source prior, so uniform average cannot cross below raw.

H30 prices Carson's public reversible dither idea. A fixed public transform
schedule:

```text
target_p = T_p(current_layer)
decode target_p, then apply T_p^-1
```

can refresh visible bytes without per-record birth/salt metadata; only the pass
count/profile is needed. But `T_p` is a bijection, so uniform entropy change is
`0`. Trying many transforms and choosing the best one costs `log2(P)` selector
bits, reducing to H15. Public dither is therefore a strong freshness scaffold
for Total-Cover or a future fertility class, not a standalone compression
source.

H31 prices the coset/syndrome/ECC witness family. A seed names a codeword `c`
and a residual repairs it to target `x`. This is statelessly decodable:

```text
x = c(seed) XOR residual
```

But full support needs `n-k` residual bits for an `n`-bit target and `k` seed
bits, so `k + (n-k) = n` before record overhead. Low-weight residuals compress
only an exponentially tiny subset: `n=64,k=32,r=4` has `12.627` bits of saving
when reachable, but only `2^-12.627` coverage. Omitting the residual requires a
checksum/referee that scales with the candidate set, reducing to H25. Recursing
on the residual does not help under uniform law because `x XOR c` is still
uniform. The only surviving use is again fertility-shaped: residual bits must
save more than one future bit each (`gamma > 1`) with uniform controls negative.

H32 tests Parfit's bits-back latent seed reservoir. Bits-back is the right
implementation of H29's latent cover marginal: it can avoid paying a
selected-cover rank and can carry a posterior tape through a fixed reverse
decode order. But the tape is conserved state. Spending one tape bit as a
best-of-salt selector has one bit of opportunity cost unless a public fertility
law gives more than one future bit of value. H32 rows with `gamma=1` are exactly
conserved or negative; positive rows require `gamma>1`. So the strongest
combined architecture collapses to:

```text
H29 collective marginal / bits-back code
+ H30 public reversible dither for freshness
+ H28 public fertility class with gamma > 1
```

This is a coherent source-shaped implementation target, but not a uniform
all-data escape.

H33 prices the de Bruijn/universal-tape address idea. A public cyclic tape that
contains every `L`-bit string exactly once gives guaranteed stateless matches,
but the coordinate has `L` bits for all-data coverage. Shorter addresses save
bits only on incomplete support: for `L=64`, a 32-bit coordinate reaches only a
`2^-32` subset. Adjacent tape overlap is real but source-shaped: `16` adjacent
8-bit windows need only `23` bits instead of `128`, but the source fraction is
`2^-105`. Public phase shifts are reversible relabelings; chosen phases cost a
selector. Thus universal tapes are useful deterministic seed-universe
scaffolds, not a new maintained recursive compression channel.

H34 tests XOR/fountain superposition, the strongest order-does-not-matter
geometry found so far. It is genuinely stateless: the decoder reads a recipe,
regenerates public seed vectors, XORs them, and order is irrelevant. The
selector ledger cancels the win. Sparse `k`-XOR over `M=2^s` vectors has at
most `C(M,k)` possible targets; under uniform targets coverage is about
`1-exp(-C(M,k)/2^n)`. Rows near full coverage already cost at least raw
entropy: `n=64,s=32,k=4` uses `123.415` unordered selector bits for a 64-bit
target, and `n=128,s=32,k=8` uses `240.701`. Full-rank public linear bases
cover all targets only with `n` coefficient bits. Random fountain recipes need
`n+1.203` bits for 90% coverage and `n+3.788` bits for 99.9999% coverage.
Extra decompositions are multiplicity tape; bits-back can conserve them but
not beat raw for uniform data. Thus XOR/fountain is a useful stateless record
and compute primitive, not the missing all-data recursive compression channel.

H35 prices confluent normal forms: records can open out of order and settle
into a canonical arrangement by public local moves. This is the clean algebraic
version of a ready/not-ready boundary or "order does not matter" decoder. It
works as machinery but not as a free information channel. A ready prefix costs
only `log2(N+1)` if readiness is public, but an arbitrary ready subset costs
`log2 C(N,m)`: for `N=1,000,000,m=100,000`, the subset costs `468,986.039`
bits, or `4.690` bits per ready record. A confluent normal form discards the
original linear extension; `128` unordered distinct items require `716.162`
order bits (`5.595` per item) to restore arbitrary order. If placement is
seed-derived instead, each placement bit is paid as one bit of lost match
supply. So confluent decode joins H21/H23/H27 as useful stateless placement,
not the missing compression source.

H36 prices the strongest biology-shaped lane: public developmental attractors,
canalization, and genotype-to-phenotype unfolding. A `g`-bit genotype can name
at most `2^g` phenotypes; roughly-all coverage of `n` phenotype bits needs
`g>=n`. Attractor dynamics do not remove this: an `n`-bit state falling into
`2^a` attractors needs `a` attractor bits plus `n-a` inverse-branch bits for
lossless arbitrary recovery. Exact 8-bit basin-prior rows show the honest DNA
lesson: a Zipf basin with entropy `H(Q)=6.222` saves `1.778` bits on source data
drawn from `Q`, but uniform targets have `9.193` bits of pure cross-entropy.
Regulatory current+future pairs similarly compress only as a source: a
32+32-bit pair named by a 32-bit genotype has `2^-32` uniform support and
32 bits of source gain. Thus developmental unfolding is a coherent stateless
Telomere-like source language and the best biology analogy, but it is a
premise shift requiring measured source entropy deficit / `gamma>1`, not an
all-data uniform escape.

H37 prices d-choice self-routing / cuckoo placement. It is the first routing
variant in this stretch that improves a live constant: if a public active lane
has fraction `r`, `d` candidate cells hit with fraction `1-(1-r)^d`. For
`r=0.10`, the lane tax falls from `3.322` bits at `d=1` to `0.812` bits at
`d=8` and `0.296` bits at `d=16`. This helps the H28/H36 fertility target
because value lift only has to beat the reduced lane tax. But exact destination
still costs about `log2(Q/d)` supply bits; selected matchings are metadata; and
content-selected compaction still pays `log2 C(N,m)` (`4.690` bits/open at
`N=1,000,000,r=0.10`). Thus H37 is useful stateless routing machinery and a
threshold reducer, not a placement/order entropy escape.

H38 combines the live source-shaped pieces. For H18's best neutral-capacity row,
`missing=4.565` bits/record, `neutral=3.819` bits/record, and
`records/atom=0.010987`, so the no-lane threshold is
`gamma_needed=1.195`. Adding a public d-choice fertility lane gives:

```text
lane_loss = -log2(1-(1-r)^d)
gamma_needed = 1.195 + lane_loss / 3.819
```

For `r=0.10`, `d=16`, the lane loss is only `0.296` bits/record and the
combined threshold is `gamma_needed=1.273`; at `d=32` it is `1.209`. Thus
d-choice routing can approach the no-lane threshold but cannot beat it because
`lane_loss >= 0`. As a standalone public fertility class, however, d-choice
makes the value-lift target much smaller: `r=0.10,d=16` needs only
`value_lift > 0.296` bits per selected record, not `3.322`. H38 therefore
sharpens the constructive target to a source-shaped two-layer kernel with
measured value lift above `-log2(1-(1-r)^d)` and random/uniform controls
negative.

H39 implements that two-layer source-shaped fertility kernel. For
`r=0.10,d=16`, the lane tax is `0.295663` bits/selected record. A fixed public
future source with two Bernoulli bits at `p=0.75` already gives `0.377` bits of
source lift and `+0.082` net after lane, while the uniform control is `-0.711`.
The exact H28 lift test also crosses: with `k=4` future children, `w=2.0` net
priced future bits per easy child, `q1=0.50`, and `q0=0.20`, measured
`E[V|C]-E[V]=0.448`, net `+0.153`; the matching uniform control has lift about
`0.002`, net `-0.293`. This is the first constructive positive row in the
post-H38 lane, but only as a public source-language positive control. It proves
the biology-shaped adjacent premise is coherent; it does not solve the
roughly-all-data uniform/content-blind goal.

H40 prices an EOF/whole-file length-code loophole. A whole-file decoder can use
EOF, so non-prefix one-to-one codes are possible. For a fixed `n`-bit virtual
board, stripping leading zeros after a public permutation saves `~1` bit on
average, with `H(length)~=2` bits, and the optimal one-to-one EOF code has
`E[L]=n-2+(n+2)/2^n`, i.e. less than two expected bits of fixed-`n` credit.
That is real but final-only: using the same fixed virtual board every pass does
not accumulate the savings. Best-of-`P` public phases need a selector;
`P=65536` gives `E best LZ=16.333` and selector `16`, a `0.333` bit constant.
To compound, the semantic board must shrink each pass, but reverse decode then
needs the ordered length reductions: geometric trim saves `~1` bit/pass while
the reduction ledger has `~2` bits/pass of entropy. If original `n` or exact
valid-bit count is not already public, storing those fields spends more than
the fixed-`n` constant (`n=128` gives ideal gain `2` vs length+pad cost
`10.011`). Thus EOF length carries a small legal whole-file side channel, not a
maintained recursive compression source.

H41 reopens the user's position-as-state idea in its strongest form:
ready-prefix compaction, public board/orbit salt, and order-insensitive child
placement. The result is not a dismissal. Position is excellent stateless
decode machinery when the selected set is public:

```text
salt = H(seed, public_phase, current_slot)
destination = public_function(record_ordinal, phase, child_index)
```

But a boundary only says how many records are ready, not which original slots
were ready. If readiness is content-selected, the hidden inverse stable
partition is `log2 C(N,R)`: at `N=1,000,000,R=100,000`, the true subset bill is
`4.689860` bits/open while the boundary is only `0.000199` bits/open. The
constructive opening is near-total cover: at `R=999,000`, the subset/exception
bill drops to `0.011413` bits/open. Sorted birth/pass cohorts show the same
shape: equal 64-way cohorts cost about `6` bits/atom, but `1%` old exceptions
cost only `0.140252` bits/atom. Thus position/compaction can help if Telomere
drives exceptions close to zero; it cannot make arbitrary sparse content hits
free.

H42 turns the search into a response-surface map rather than another isolated
verdict. The axes are now explicit: content-selected set entropy, public lane
supply loss, near-total exception rate, paid witness gap, source/fertility
value lift, and decoder observation class. Representative coordinates:

```text
r=0.10: subset/open=4.690, d16 public-lane loss=0.296
P=256, eps=0.010: exception ledger=0.160737 bits/atom
H7 raw first-hit delta: missing=1.357 bits/selected record
H9 fixed slack 0: missing=1.261 bits/selected record
```

This is now the scientific map for future attempts: a candidate must name which
axis it moves and by how much. The smallest source-shaped constructive target
remains a public fertility lane with d-choice routing and measured value lift
above `-log2(1-(1-r)^d)`, with uniform controls negative.

H43 answers the user's all-block replacement target in the right units. The
all-block branch genuinely removes birth/open entropy, but the active blocker
is the paid witness margin. Current high-arity Total-Cover rows are sparse in
records: H7 has `0.008789` records/input atom, so `2 bits/record` is only
`0.017578 bits/input atom`. That means exception ledgers must be compared to a
small atom budget in the current regime: with an H7-style `1.357 bits/record`
surplus, the maximum exception fraction is only `0.00059161` at `P=256`. Under
a stronger future premise of `2 paid bits per rewritten input atom`, the same
near-total formula is much looser: with fallback overhead `F=3`, coverage
thresholds are `86.887%`/`88.557%`/`90.835%` for `P=64/256/4096`. H43 also
quantifies the user's local option-count dividend: an atom participates in
`K(K+1)/2` intervals, worth an ideal `3.907` bits at `K=5` and `13.011` bits
at `K=128` before non-overlap and witness costs. Thus the option-statistic
intuition is real; it still has to survive a paid whole-cover witness.

H44 normalizes the collective-cover witness idea. The legal stateless object is

```text
Q_raw(x) = sum_{covers c expanding to x} 2^-L(c)
Q(x) = Q_raw(x) / Z
```

so the decoder can arithmetic-decode the previous layer under public `Q`
without a selected-cover rank. Exact tiny rows show duplicate-cover savings are
real, but normalization restores the uniform conservation law:

```text
E_uniform[-log2 Q(X)] = n + KL(U || Q) >= n
```

For example, `N=12,B=1,K=4,D=8` has best local selected-cover cost `33.455322`
bits and raw `-log2 Q_raw=26.245017`, but the normalized public code averages
`12.221970` bits for a 12-bit uniform layer. H44 is therefore the cleanest
stateless collective witness mode and a legitimate public source prior, not a
uniform all-data escape.

H45 tests the most direct genetics-shaped recursion mechanism: neutral
selection. If `M` same-cost witnesses decode to the same current span, the
encoder can choose the witness with the most fertile descendants while the
decoder still reads an ordinary seed. This is real Telomere-native machinery,
but under the uniform future-saving tail it is conserved:

```text
Pr[S >= s] <= 2^-s
Pr[max_i S_i >= log2(M) + k] <= 2^-k
```

Exact H45 rows with `M=2^b`:

```text
b=3.819: E[max]=4.202, increment=3.202, gamma_increment=0.839
b=8.000: E[max]=8.336, increment=7.336, gamma_increment=0.917
b=16.000: E[max]=16.333, increment=15.333, gamma_increment=0.958
```

The best H18 neutral row needs `gamma > 1.195`, so uniform neutral selection
misses. Source-shaped heavier tails can add absolute future value, but that is
a public developmental/fertility premise, not a content-blind neutral-selection
amplifier. This leaves the biology-shaped target precise: a fixed public
developmental universe must demonstrate measured `gamma > 1` or value lift on
held-out source data, with uniform controls negative.

H46 isolates the user's high-arity option-statistic intuition. An interior atom
belongs to `K(K+1)/2` intervals, so the ideal local best-of-options dividend is
real: `3.907` bits at `K=5`, `13.011` bits at `K=128`, and `15.006` bits at
`K=256`. The nearest paid rows are also genuinely close in record units: H7's
`1.357 bits/record` miss is only a `2.562x` effective-choice factor, H9's
`1.261 bits/record` miss is `2.397x`, and the H12 perfect-credit upper bound
needs only `1.677x`. This validates high arity as the right finite surface to
probe. The blocker is that the winning option itself must be public, derived,
or paid. In selector notation, `H(R_min)` gains about `log2 M`, but `H(J)` for
the winning option costs about `log2 M`, so the full `(J,R_min)` description
returns to the same entropy scale unless a normalized source/fertility prior is
doing real work.

H47 then tests the most direct public follow-up: center each selected width on
the H11 selected-extreme mode and arithmetic-code a frozen residual table
trained on independent uniform-law covers. The bounded `B=4,K=128,D=512`
calibration stays stateless and parseable but moves away from the target:

```text
train-selected law = m1/arity_bucket
held-out gain = -0.089252 bits/input atom
missing = 7.030 bits/selected record
records/atom = 0.012695
avg arity = 78.77
residual bits/record = 6.775
```

So the missing piece is not simply "add a richer public residual table." Extra
table shape has to beat its own normalized support entropy on held-out data.
The live systematic target is narrower now: capture the remaining H7/H9
`~1.3 bits/record` with decoder-visible structure, or demonstrate a true
source/fertility value lift while uniform controls stay negative.

H48 tests a decoder-inference variant that looked like it might remove one
channel cleanly: embed arity/type into the seed grammar, so the decoder derives
arity from the witness instead of reading an arity field. Under the uniform
hash law, a seed class with public mass `q_a` has first-hit ranks shifted by
`-log2(q_a)`. Thus the expected class tax is:

```text
E[-log2 q_A] = H(A) + KL(P_A || q)
```

which is exactly the arithmetic-coded arity bill at the optimum. The kernel
confirmed the distinction between an oracle boundary and a legal stream. At
`B=4,K=128,D=512`, the non-parseable fixed-width lower bound crosses:

```text
arity_seed_fixed_lower/global = +0.217773 bits/input atom
```

but the parseable seed-only forms miss:

```text
arity_seed_j3d1/global    = -0.128906 bits/input atom, missing 7.333 bits/record
arity_seed_j3d1/remaining = -0.127930 bits/input atom, missing 7.706 bits/record
arity_width_grammar/rem   = -0.124392 bits/input atom, missing 9.798 bits/record
```

So H48 is not a dismissal of the intuition. It shows that arity can be
statelessly derived from the seed, but the remaining bill is witness
self-delimitation and cover/width boundary, plus the lost seed supply from
reserving seed classes. The next systematic target is no longer another arity
syntax trick; it is the all-block reproduction number:

```text
rho_t = paid_bits(layer_{t+1}) / raw_bits(layer_t)
need held-out E[log rho_t] < 0
```

with the serialized selected records fed into the next pass and every
arity/width/profile/exception selector paid.

H49 implements that all-block reproduction-number probe. It treats the paid
record stream from each total-cover pass as the next layer's fresh target bits,
then re-atomizes and repeats. This keeps the user's intended all-block premise:
no carried records, no birth/open entropy, and no salt-pass ambiguity. Under the
uniform hash law, freshness is automatic; the pass/fail condition is instead:

```text
rho_t = paid_bits(layer_{t+1}) / padded_bits(layer_t)
need held-out E[log rho_t] < 0
```

The bounded default `B=4,K=128,D=512`, `passes=5`, `trials=6` result:

```text
oracle_free_boundary: mean log2 rho = 0.001801, geometric rho = 1.001249
h7_raw_delta:         mean log2 rho = 0.011287, geometric rho = 1.007854
h9_fixed_slack0:      mean log2 rho = 0.011568, geometric rho = 1.008051
```

Thus the all-block branch does maintain fresh dice, but the current paid H7/H9
laws still expand when iterated. The result is intentionally not a broad
negative theorem: H49 is the new scoring harness. Future candidate modes should
be judged by repeated-pass `E[log rho]`, not by a single lucky one-pass row or
by freshness alone.

H50 sweeps the H49 reproduction score around the closest high-arity paid rows.
The compact default sweep again showed oracle recursion can cross while paid
rows miss. A scout then caught an important false-negative risk: `atoms=96`
clips `K=128+`, so H50 reran the live high-arity rows with `atoms >= K`. The
corrected sweep:

```text
B=4,K=128,D=448,atoms=160:
  oracle=-0.004500, h7=+0.015741, h9 s0=+0.016565, h9 s1=+0.009166
B=4,K=128,D=512,atoms=160:
  oracle=-0.007947, h7=+0.014601, h9 s0=+0.004884, h9 s1=+0.014554
B=4,K=192,D=672,atoms=192:
  oracle=-0.002221, h7=+0.010381, h9 s0=+0.008074, h9 s1=+0.007749
B=4,K=192,D=768,atoms=192:
  oracle=+0.003740, h7=+0.005161, h9 s0=+0.013468, h9 s1=+0.007313
```

Best paid row:

```text
B=4,K=128,D=512,H9 slack0
mean log2 rho = +0.004884
geometric rho = 1.003391
```

Best oracle lower bound at the same corrected target:

```text
B=4,K=128,D=512
mean log2 rho = -0.007947
geometric rho = 0.994507
```

This is the closest repeated-pass paid target measured so far, and it is still
expanding. H50 therefore narrows the next move: do not spend the next slot on
more arity syntax or per-file residual tables. The genuinely different paid
witness is normalized collective-cover coding:

```text
Q_raw(x) = sum_{covers c -> x} 2^-L(c)
Q(x) = Q_raw(x) / Z
paid_bits(x) = -log2 Q(x)
```

H44 already proves uniform average cannot drop below raw once `Q` is normalized:

```text
E_uniform[-log2 Q(X)] = n + KL(U || Q) >= n
```

but H51 should still implement the repeated-pass/renormalization view for tiny
exact states, because it is the cleanest way to measure the exact source/prior
lift a Telomere-native collective witness would need.

H51 runs that exact normalized-`Q` reproduction diagnostic. It reports expected
bits, log-rho, below-raw fraction, and the best raw-escape mixture. Exact rows:

```text
N=10,B=1,K=4,D=8:  avg=10.160503, excess=0.160503, below_raw=0.416016, alpha=0.00
N=12,B=1,K=4,D=8:  avg=12.221970, excess=0.221970, below_raw=0.373779, alpha=0.00
N=10,B=1,K=4,D=10: avg=10.118241, excess=0.118241, below_raw=0.425781, alpha=0.00
N=8,B=2,K=4,D=8:   avg=17.384658, excess=1.384658, below_raw=0.181320, alpha=0.00
```

So collective covers do create a real minority-win/source-prior lane: many
individual strings fall below raw. But for uniform roughly-all data, normalized
expected length remains above raw and the best raw-escape mixture chooses
`alpha=0`. H51 closes the cleanest hidden-cover branch as a uniform escape and
recasts it as a source/fertility target with a measurable required lift.

H52 returns to the tight H50 gap with a faster high-`K` fixed-slack scout. It
samples H9's fixed-width event directly:

```text
width(a) = min(D, aB - slack)
p_hit(a) = 1 - exp(-2^(width(a)-aB))
```

This preserves the H9 accounting while avoiding first-rank objects. The
default strict-cover repeated-pass rows:

```text
B=4,K=128,D=512:
  s0=+0.006713, s1=+0.009618, s2=+0.012788 mean log2 rho
B=4,K=192,D=768:
  s0=+0.003658, s1=+0.005784, s2=+0.007849 mean log2 rho
```

A focused `K=256` strict-cover scout with `atoms=512`:

```text
B=4,K=256,D=1024:
  s0=+0.004849, s1=+0.003775, s2=+0.005391, s3=+0.007273 mean log2 rho
```

So higher `K` and fixed slack move the frontier in the right direction but do
not cross. Extra slack saves bits per selected record, but the interval graph
thins quickly (`p_s ~= 0.632, 0.393, 0.221, 0.118` for `s=0..3`), and the
saved bits are returned through coverage geometry, arity entropy, and padding.
The next paid boundary mechanism is a global slack ladder: choose among a small
public slack set per layer/pass and charge the slack selector. Local slack
relaxation would reintroduce the width stream and must be priced as such.

H53 tests that global slack ladder with shared nested hits, not independent
redraws. For each interval it samples one exponential first-hit variable and
then treats a higher-slack hit as a subset of lower-slack hits:

```text
hit_s(a) iff E <= 2^(min(D, aB-s) - aB)
selector cost = log2 |S|
```

The bounded `B=4,K=192,D=768,S={0,1,2}` repeated-pass row:

```text
paid_best:          +0.004480 mean log2 rho
oracle_unpaid_best: +0.001973 mean log2 rho
H52 strict s0:      +0.003658 mean log2 rho
```

The ladder is stateless when the layer header carries the slack selector, but it
does not cross after paying that selector. A headerless trial-decode rule is
free only if the compressed stream plus public rules prove a unique surviving
slack. Otherwise the missing bill is `log2 |valid slacks|`, and a checksum
referee pays `b >= log2(R-1)+lambda` bits to suppress false survivors. H53
therefore turns slack adaptation into a clean response-surface result: useful
geometry, no free channel yet.

H54 specializes the checksum/referee ledger to H53-style adaptive global
profiles. If one pass chooses one profile from `S` public profiles, then `P`
passes leave `S^P` profile sequences before the referee:

```text
P * log2(S) <= C - lambda
P_max = floor((C - lambda) / log2(S))
```

With `lambda=32`, representative selector windows are:

```text
C=64,  S=3:  20.190 global selectors
C=128, S=3:  60.569 global selectors
C=256, S=3: 141.328 global selectors
```

So a checksum can referee a bounded adaptive-profile demo, but not arbitrary
passes. It also cannot rescue the current H53 row because even the unpaid
selector-hidden lower bound remains positive.

H55/H56 test the more interesting syntax-derived variant. H55 enumerates tiny
exact languages for records of the form:

```text
[arity syntax][payload of width min(D, aB-s)]
```

Fibonacci/Zeckendorf-style arity syntax produces zero ambiguous slack streams
in the tiny exact rows, while fixed-width and Elias-gamma arity syntax leave
overlaps. That is a real decoder observation: in some grammars the slack can be
derived from syntax rather than stored.

H56 then charges that syntax in the repeated-pass target:

```text
B=4,K=192,D=768
gamma headerless:     +0.026707 mean log2 rho
fibonacci headerless: +0.023081 mean log2 rho
```

This misses by much more than H52/H53. The self-synchronizing idea is therefore
a useful decoder-proof tool, not the current compression breakthrough. Its
delimiter bits are too expensive as the primary high-`K` arity language.

H57 implements the second scout's strongest remaining axis: normalized
collective-cover `Q` at the H52/H53 high-`K` frontier. It sums all matching
covers as latent mass:

```text
Q_raw(x) = sum_{covers c -> x} 2^-L(c)
Q(x) = Q_raw(x) / Z
paid_bits(x) = -log2 Q(x)
```

This avoids transmitting the selected cover. The best listed frontier row is
very close in the repeated-pass diagnostic:

```text
B=4,K=384,D=1536,N=384:
  mean log2 rho = +0.000166
  expected excess = +1.426544 bits
```

That still misses. The geometric/log-rho surface is near flat, but the honest
uniform expected-length diagnostic remains above raw. H57 is the strongest
evidence so far that the final boundary is the normalized public witness
distribution itself, not open/carry, birth pass, final position, or selector
syntax.

H58 replaces H57's uniform legal-arity model with a frozen public arity model
trained on independent uniform-law samples. This is legal because the model is
not fit to the target layer. It improves the expected-excess frontier:

```text
H57 uniform Q, K384: +1.426544 expected excess bits
H58 bucket Q,  K384: +0.229195 expected excess bits
```

The row still misses:

```text
B=4,K=384,D=1536,N=384,bucket:
  expected excess = +0.229195 bits
  mean log2 rho = +0.000215
```

A four-sample H58 K256 row briefly went negative, but a 48-sample held-out
rerun returned positive. That is exactly the expected finite-sample trap under
the normalized public-Q theorem:

```text
E_U[-log2 Q_T(X) | T] = n + KL(U || Q_T) >= n
```

H59 then tests the fully priced raw/stopping mixture:

```text
M(x) = (1-alpha)U_n(x) + alpha/T * sum_t Q_t(x)
```

The frontier scout did not convert minority Q wins into expected compression:

```text
K384,T=1: train alpha=0.2, eval excess=+0.053411
K384,T=4: train alpha=0,   eval excess=0
```

So raw fallback and bounded stopping are valid stateless mechanisms, but not a
uniform all-data breakthrough when fully priced.

H60 quantifies the remaining "roughly all data" claim directly. For a paid
final code that saves `S` bits, the largest uniform winning fraction is:

```text
prefix/public normalized: 2^-S
EOF one-shot:             < 2^(1-S)
```

EOF/non-prefix one-shot coding can make almost every fixed-length string shrink
by one bit if the old length is free. Recursion returns the bill through the
intermediate length path:

```text
path bits = log2 C(S-1, P-1)
```

The exact tiny selector ledger makes the hidden channel visible:

```text
n=4,P=2,s=1:
  prefix slots = 4/16
  EOF one-shot = 7/16
  best-of-4 profiles, selector free = 16/16 apparent
  best-of-4 profiles, selector paid = 4/16
  checksum C_eff=1 = 8/16 apparent, 1 profile bit still owed
```

And the source-lift ledger prices "roughly all" claims:

```text
S=128,c=0.90 needs lift=3.06e38 and KL deficit=114.731004 bits
```

This is the sharpest current boundary. Any future uniform/content-blind
proposal must either exhibit a public invariant that fixes state/length/profile
paths without reducing the eligible fraction, or name a non-uniform source/value
premise.

H61 turns the current evidence into a phase diagram so future work can be
ranked by the missing honest bits rather than by intuition. The nearest
public-code misses by atom are:

```text
H59 raw/Q mixture T1: +0.053411 bits/layer = +0.000139 bits/atom
H58 frozen bucket Q:  +0.229195 bits/layer = +0.000597 bits/atom
```

Those are source-alignment targets, not uniform breakthroughs, because the
uniform public-code check remains `E_U[-log2 Q(X)] = n + KL(U || Q) >= n`.
The nearest paid witness targets remain the total-cover gaps:

```text
H12 perfect-credit upper bound: 0.746 bits/record, 0.008196 bits/atom
H7 raw first-hit total cover:   1.357 bits/record, 0.011929 bits/atom
H9 fixed slack 0:               1.261 bits/record, 0.012314 bits/atom
```

This creates the most useful split for the next scientific pass: a uniform
candidate must find a public invariant that breaks the current conservation
ledger, while a DNA/source-shaped candidate must name and measure the
non-uniform fertility/value lift instead of treating it as free.

H62 prices that DNA/source-shaped branch as a public fertility class. If a
public class `F` has uniform mass `f`, the witness/code distribution gives it
per-state lift `a`, and the source visits it with probability `c`, then the
relevant score is:

```text
score(x) = log2(Q(x) / U(x))
crossing requires E_source[score] > target_bits
```

The nearest public-code misses need only modest enrichment in this toy law:

```text
f=0.10,a=2:
  H59 c* = 0.1454, enrichment = 1.454x
  H58 c* = 0.1458, enrichment = 1.458x
  H7 atom c* = 0.1554, enrichment = 1.554x
```

But selected-record witness gaps are much harder:

```text
f=0.10,a=8:
  H12 witness c* = 0.5640, enrichment = 5.640x
  H7 witness c*  = 0.6822, enrichment = 6.822x
```

So the live constructive target is not "find more ordinary patterns." It is a
public Telomere fertility/source law with the recursive invariant
`c_t >= c*` and `c_{t+1} >= c*`, plus uniform negative controls.

H63 prices that recursive invariant as transition dynamics:

```text
c_{t+1} = c_t * p_FF + (1-c_t) * p_OF
```

With background inflow equal to the class mass (`p_OF=f`), the nearest
atom-level public-Q/source targets need only moderate self-renewal:

```text
H59 atom, f=0.10,a=2,c*=0.1454: min p_FF = 0.4122
H58 atom, f=0.10,a=2,c*=0.1458: min p_FF = 0.4141
H7 atom,  f=0.10,a=2,c*=0.1554: min p_FF = 0.4565
```

The selected-record witness-gap route is far harder:

```text
H7 witness, f=0.10,a=8,c*=0.6822,p_OF=0.10: min p_FF = 0.9534
H7 rare witness, f=0.01,a=64,c*=0.3776,p_OF=0.01: min p_FF = 0.9835
```

That makes the current best constructive target: whole-cover/public-Q
atom-level crossing first, then prove a public recursive fertility invariant.

H64 reopens EOF/final-length coding as a serious starting point and pins down
exactly where it fails for arbitrary repeatable stateless recursion. For
`n=128`, minimum one bit saved per pass:

```text
P=1:  stateless variable fraction ~= 1.000000
P=2:  stateless variable fraction ~= 0.500000, path-free apparent ~= 1.000000
P=4:  stateless variable fraction ~= 0.125000, path-free apparent ~= 1.000000
P=8:  stateless variable fraction ~= 0.007812, path-free apparent ~= 1.000000
P=16: stateless variable fraction ~= 0.000031, path-free apparent ~= 1.000000
P=64: stateless variable fraction ~= 1.084e-19, path-free apparent ~= 0.535193
```

The path-assisted row is the tempting one: for fixed small `P`, variable
non-prefix shrink can cover almost all long strings. But the decoder only gets
that row if the per-pass length path is available. At `n=128,P=64,s=1`, H64
measures:

```text
average path bits ~= 114.186748
max path bits ~= 123.171434
bucket+path entropy bits ~= 118.681150
```

So final-board/EOF proposals now have a precise burden: derive the length path
publicly without reducing coverage to the stateless final-output bound
`2^(1-P*s)`.

H65 generalizes that into a finite public-invariant exhaustion ledger. It
reduces fixed boards, public permutations, CRT clocks, affine/Feistel orbits,
canonical normal forms, EOF trims, public lanes, and profile schedules to:

```text
how many final visible states can the decoder distinguish?
```

For `n=16,P=4,s=1,A=3,lane=0.1,C=16,lambda=4`:

```text
EOF visible final states:    charged fraction 0.124985
variable path hidden:        apparent 0.989365, hidden 2.984750, charged 0.124985
best-of profile path paid:   apparent 1.000000, paid selector 6.339850, charged 0.124985
public lane mask:            public loss 3.321928, charged 0.012498
```

Checksum/referee bits can buy finite demos, but only up to `C-lambda`. Once the
hidden path/profile stream exceeds that finite budget, the same selector
channel returns.

H66 addresses the high-arity all-block option argument directly. The local
option dividend is real:

```text
M(K) = 1 + 2 + ... + K = K(K+1)/2
```

But the non-overlapping cover chosen after seeing content has its own selector
scale. The number of cover shapes for `N` atoms with parts `1..K` has entropy
rate `h_K = log2(lambda_K)` with `sum lambda_K^-a = 1`. Representative rows:

```text
K=5:   local log2 M = 3.907, cover entropy = 0.975225 bits/atom
K=16:  local log2 M = 7.087, cover entropy = 0.999989 bits/atom
K=128: local log2 M = 13.011, cover entropy = 1.000000 bits/atom
```

Current paid misses are much smaller per atom:

```text
H12: 0.008196 bits/atom
H7:  0.011927 bits/atom
H9:  0.012314 bits/atom
H58: 0.000597 bits/atom
H59: 0.000139 bits/atom
```

That explains why high arity feels extremely close. The hidden cover-choice
reservoir is huge compared with the miss. But if it is used after seeing
content, it is a selector; if it is normalized as public collective `Q`, the
uniform expected length obeys the same KL conservation.

H67 adds a guardrail for future all-block reproduction rows. A negative
`E[log2 rho]` can coexist with uniform conservation if rare expansions carry
the bill. In a two-outcome toy law with `rho=a<1` normally and `rho=b>1` with
probability `eps`, choosing `b` so `E[rho]=1` gives:

```text
a=0.99, eps=0.01:
  b = 1.990
  E[log2 rho] = -0.004427
  P=64:   Pr(at least one blowup) = 0.474404
  P=256:  Pr(at least one blowup) = 0.923685
  P=4096: Pr(at least one blowup) ~= 1.0
```

So `mean log2 rho < 0` is necessary for a repeated-pass candidate, but not
sufficient for "roughly all data over arbitrary P." Future RG rows must also
report the bad-tail/blowup budget or prove exact zero bad fraction.

H68 makes the same optional-stopping point on a finite exact public-code
domain. For any normalized public `Q`, `W(x)=Q(x)/U(x)` has `E_U[W]=1` and
`E_U[-log2 Q(X)] >= n`. In the `2^8` toy audit:

```text
spiky public Q:          excess +0.336062, E[W]=1, Pr(save>=1)=0.062500
lane public Q:           excess +0.419518, E[W]=1, Pr(save>=1)=0.250000
raw/Q mixture alpha=.75: excess +0.047701, E[W]=1, Pr(save>=1)=0
hidden best-of profiles: hidden selector gain 1.009249 bits
```

The hidden best-of row shows the trap directly: post-selecting the best public
profile creates apparent gain only while profile identity is unpaid. Public
mixture restores the normalized conservation check.

H69 fixes a measurement issue in the total-cover runner before future high-K
refinement. The old 49..512-bit span path rounded log-rank up to a power of two
before computing Lotus width. The corrected generator keeps the exponential
race sample in log space for width calculation. With 10,000 samples per span:

```text
target bits 192: corrected width 190.679400, old rounded width 191.679400
target bits 512: corrected width 510.653500, old rounded width 511.653500
```

So old high-span rows were conservatively overcharged by about one payload bit
per selected record. This can move frontier constants, but not the uniform-law
conservation result by itself.

H70 turns the response map into an explicit scientific protocol. Future lanes
are no longer just "try an idea"; each candidate must name the changed knob,
the predicted movement, the paid currency, the adversarial control, and the
stop rule. The current numeric axes are:

```text
H12 perfect-credit upper: miss 0.746 bits/record, needs 1.677x effective choices
H7 raw first-hit:         miss 1.357 bits/record, needs 2.562x effective choices
H9 fixed slack 0:         miss 1.261 bits/record, needs 2.397x effective choices
r=0.10 public lane:       d=26 for <=0.10 bits loss, d=48 for <=0.01 bits loss
H59 source target:        f=0.10,a=2 needs c*=0.1454 and p_FF=0.4121 with p_OF=f
tail guard:               eps=0.001 allows Pr(blowup)<=0.50 only through P=692
```

This is now the handoff rule: a new Telomere-recursion idea is promising only
if it predicts enough movement on one of those axes, while the paired uniform
or adversarial control stays honest.

H71 makes the finite-pass "roughly all data" boundary explicit. For any
structure-free injective code, the fraction of `n`-bit uniform inputs that can
finish at least `S` bits shorter is bounded by `2^-S` for prefix/public
self-delimiting streams, or by the generous EOF one-shot bound `2^(1-S)`.
Therefore at `90%` coverage:

```text
>=1 bit/pass:
  prefix/self-delimiting stream: K = 0
  generous EOF one-shot bound:   K = 1

>=2 bits/pass:
  prefix/self-delimiting stream: K = 0
  generous EOF one-shot bound:   K = 0
```

This is the sharp finite `K` under the strict "roughly all data, not reliant on
structure" premise. Maintained positive-rate recursion over arbitrary `P`
therefore needs a public invariant outside the count, a paid channel beaten
elsewhere, or a non-uniform source/fertility law.

H72 prices the best-of-profile, checksum-referee, cover-shape, and visible
final-state multiplier trap. In an exact `n=16,S=4` tiny count, `16` free
profiles raise prefix coverage from `0.0625` to `1.0`, but once the selector is
paid inside the short output, coverage returns to `0.0625`. A finite referee
can choose among finite profiles, but charged referee bits cancel in the same
way. Public `Q` is the normalized form of the idea, and its uniform expected
excess remains nonnegative.

H73 keeps final-board / egg-carton geometry alive, but prices it as visible
state. For `N=12,R=4,P=8`, sparse ready-plus-birth history needs `20.951`
bits. A `Q=N` occupancy board supplies `8.951` bits, enough for the ready
subset but short by the `R log2 P` birth labels. A `Q=N*P` expanded board
supplies `21.664` occupancy bits, but those are visible coordinate bits in the
compressed file. Public lanes instead pay match-supply loss.

H74 tests the strongest collective witness language exactly: latent normalized
whole-cover `Q`, where the selected cover is never transmitted and all
cover/record descriptions contribute Kraft mass to `Q_raw(x)`. Tiny exact
domains show real duplicate-cover gains, but still positive uniform excess:

```text
B=2,N=8,K=4,D=8:   Q excess +1.673076 bits, best raw/Q alpha 0.00
B=1,N=12,K=6,D=8:  Q excess +1.814795 bits, best raw/Q alpha 0.00
B=4,N=4,K=4,D=8:   Q excess +6.803412 bits, best raw/Q alpha 0.00
```

So latent whole-cover `Q` remains the best source-shaped witness language, not
a structure-free uniform escape.

H75 closes the rare-blowup loophole. For prefix/self-delimiting codes with a
winner fraction `c`, total saving `S`, and non-winners bounded to expand by at
most `B` bits, Kraft gives:

```text
c * 2^S + (1-c) * 2^-B <= 1
```

Thus bounded losers do not create a roughly-all winning set; as `B` grows the
bound approaches `c <= 2^-S`. For a claimed `90%` typical shrink over
`P=64,s=1`:

```text
S = 64
loser expansion needed for mean balance = 576 bits
per-pass bad-tail eps for 90% survival <= 0.001645
prefix winning coverage bound = 5.421e-20
EOF winning coverage bound    = 1.084e-19
```

Rare blowups can pay an average-length debt, but they cannot create short
outputs for the claimed majority, and unbounded bad tails violate Telomere's
bounded-loss contract.

H76 closes randomized/search-driven best-of codebooks under the same accounting.
Conditioned on public randomness, the compressor is one deterministic public
code. Private encoder randomness must be stored or decode is not lossless. A
best-of `M` profile search has apparent free coverage `M * 2^-S`, but paying
`log2 M` selector bits cancels the multiplier. For `90%` coverage at
`P=64,s=1`, the prefix best-of route needs about `2^63.848` profiles, which is
also `63.848` selector bits. Compute can find the best profile; it cannot make
the profile identity free.

H77 tests the last constructive-looking loophole: Telomere's own public
record/cover language might create a self-induced fertility source. In the
abstract public-class rows, `f=0.10,a=2` needs `c*~0.145` and `p_FF~0.41`, but
uniform starts at `c0=f=0.10` and an unrestricted/whitened code stream returns
to `F` at only `p_FF=f`. In the exact H74-derived high-`Q` class
(`B=1,N=12,K=6,D=8`, top 10% by `log2(Q/U)`), the requirement is harsher:

```text
H59 atom miss: c*=0.5075, random p_FF=0.1001, required p_FF=0.9029
H58 atom miss: c*=0.5076, random p_FF=0.1001, required p_FF=0.9029
H7 atom miss:  c*=0.5102, random p_FF=0.1001, required p_FF=0.9039
```

So self-induced fertility remains a legal public source-law target, but it is
not a structure-free all-data escape. It needs strong measured retention or a
paid public lane/supply restriction.

H78 states the unified theorem boundary: after every visible state, selector,
referee, final board, random/profile identity, and bad-tail cost is counted, a
content-blind stateless lossless scheme covering fraction `c` with total saving
`S=P*s` obeys:

```text
prefix/self-delimiting: c <= 2^-S
EOF one-shot generous:  c <= 2^(1-S) - 2^-n
```

For `c=0.90,s=1`, max finite `K` is `0` prefix or `1` EOF. For arbitrary `P`,
allowed average saving per pass tends to zero. The single constructive
relaxation left is a predeclared non-uniform public source/fertility law with
uniform negative controls and full on-disk accounting.

H79 audits the public d-choice fertility lane that H77 left as the nearest
constructive-looking target. The key distinction is placement choice versus
witness choice. If one stored record has `d` public candidate cells, the decoder
can recompute a canonical position and the placement lane loss is
`-log2(1-(1-r)^d)`. But if the encoder uses `d` alternative seed witnesses to
bias the next record-value stream into a fertile class, the multiplicity itself
is an information channel costing about `log2(d)`.

For example:

```text
r=0.10,d=16: placement loss=0.296, log2(d)=4.000,
             class KL made=2.043, fake net=+1.747, honest net=-1.957
r=0.10,d=23: placement loss=0.134, log2(d)=4.524,
             class KL made=2.609, fake net=+2.475, honest net=-1.914
```

This blocks the reward-hack version of "cheap d-choice fertility". Public
position/salt lanes remain useful decode geometry, but they do not create a
free high-fertility byte/value source. The next surviving experiment must keep
position/phase refresh separate from witness-value selection, or measure real
value lift above `current_miss + lane_loss` without borrowing uncharged
witness-choice bits.

H80 then turns the surviving source-shaped lane into an exact finite-domain
target instead of a hunch. On the H74 tiny public `Q` domain
(`B=1,N=12,K=6,D=8`):

```text
E_U log2(Q/U) = -1.814795  -> uniform excess +1.814795 bits
E_Q log2(Q/U) = +1.365022  -> Q-source saving +1.365022 bits
```

Sweeping public high-`Q` classes shows that H77's top 10% class was not the
best source-shaped target. A gentler class around `f=0.25` works better:

```text
top 25%:          Q(F)=0.7787, mu_F=1.279, mu_O=-2.846, lane16=0.015
F_positive Q>U:   Q(F)=0.7839, mu_F=1.254, mu_O=-2.866, lane16=0.013
bottom 25%:       Q(F)=0.0079, mu_F=-5.479, opposite lift
```

For the scaled H7 target in this exact toy domain:

```text
f=0.25: c*=0.7247, Q(F)=0.7787, Q(F)-c*=+0.0540
```

This is useful progress, but it is source-shaped progress. It says the next
candidate must produce or preserve this public high-`Q` output law across
passes, with measured `p_FF`/`p_OF`, while the uniform row remains negative.
It does not lift the H78 all-data bound.

H81 checks the immediate recurrence objection: if `Q` is the source, why not
just entropy-code under `Q` and run the next pass? On the same exact domain:

```text
raw visible word bits:          12.000000
H(Q):                           10.634978
D(Q||U) source redundancy:       1.365022
D(U||Q) uniform Q-code excess:   1.814795
```

For the `top25` class:

```text
entropy-coded Q:  next c=0.2500, gain=1.365, shape cost=0.000, H7? no
visible Q-shaped: next c=0.7787, gain=1.365, shape cost=1.365, H7? yes
raw/permutation:  next c=0.7787, gain=0.000, shape cost=0.000, H7? yes
```

So ordinary compact coding spends the source redundancy and whitens the visible
next layer back to the uniform class rate. Making the visible next layer
`Q`-shaped again preserves fertility, but the distribution-shaping slack spends
the same `D(Q||U)` bits. Public reversible transforms can preserve `F`, but do
not shrink the layer. The remaining target is therefore narrower and cleaner:
find a native Telomere record syntax whose compact visible output is already
high-`Q`/fertile, rather than entropy-coding to uniform bits and reshaping.

H82 tests the simplest native-syntax version: make valid visible strings be a
public fertile subset `F`. If `f=U(F)` and `q=Q(F)`, then:

```text
support tax               = -log2(f)
class-membership dividend =  log2(q/f)
forced-subset net         =  log2(q) <= 0
```

Exact rows:

```text
top25:      Q(F)=0.7787, support tax=2.000, dividend=1.639, net=-0.361
F_positive: Q(F)=0.7839, support tax=1.971, dividend=1.619, net=-0.351
top50:      Q(F)=0.9398, support tax=1.000, dividend=0.910, net=-0.090
```

So "valid strings are fertile strings" is not the missing free channel. A
surviving native syntax has to be graded: a full public probability law over
record strings whose code lengths and visible fertility are aligned, not merely
a valid/invalid support restriction.

H83 tests the scout's Kraft-preserving relabeling idea. On the exact H80
domain, a length-preserving relabeling is a permutation of visible words. For a
fixed source law `Q` and fixed class `F`, the optimal permutation simply places
the largest `|F|` probabilities in `F`. For the relevant top-`Q` classes,
identity already does that:

```text
top25:      identity Q(F)=0.7787, optimal Q(F)=0.7787, c*H7=0.7247
F_positive: identity Q(F)=0.7839, optimal Q(F)=0.7839, c*H7=0.7304
```

For bottom/random classes, a best relabeling can move high-`Q` mass into the
class, but that is just choosing a different public profile/class. If adaptive,
the profile channel is enormous:

```text
log2 C(4096,1024) ~= 3316.9 bits
```

So length-preserving relabeling is not the missing mechanism. It remains legal
as a frozen public design choice, but the remaining native-syntax target is a
graded public record law, not a permutation chosen to make a class look fertile.

H84 tests that graded public record-law target in the cleanest finite form.
Let `R_lambda` be a visible law tilted between uniform `U` and H80's fertile
source `Q`:

```text
R_lambda(x) proportional to U(x) * 2^(lambda * log2(Q(x)/U(x)))
```

The one-shot `Q -> R` tradeoff is real:

```text
lambda=0.90: Q->R saving=0.216226 bits, R(top25)=0.738867
```

This preserves the scaled-H7 top25 threshold while still shrinking once. But
after that pass, the next input law is `R`, not `Q`. The recursive invariant is:

```text
R -> R saving = 0
```

Encoding `R` under `Q` is expanding unless `R=Q`. Therefore graded `Q`-family
native laws can give transitional compression, but not maintained recursive
compression by themselves. The next target is sharper: find a high-entropy
fertile law where fertility is not merely the entropy deficit of `Q`. This is
the value/count separation problem in its cleanest form so far.

H85 turns that target into a budget frontier. Under the ideal content-blind
future-value tail:

```text
Pr_U[V >= s] = 2^-s
```

a public source with entropy deficit `delta = D(P||U)` can, in principle, tilt
toward higher future value. The important rows are:

```text
delta=0.017703 bits -> lift-delta=0.216226 bits
delta=0.101121 bits -> lift-delta=0.500000 bits
delta=0.457214 bits -> lift-delta=1.000000 bits
```

So high-entropy fertility is not mathematically absurd: a small entropy budget
can buy more future-value lift than it costs in this ideal tail model. But H85
is only an upper-bound target, not a Telomere mechanism. The missing piece must
be a public, stateless native syntax whose measured future-value tail actually
has this separation while uniform controls stay negative after the same
accounting. This keeps the biology-shaped value/count-separation lane alive,
and makes it experimentally precise.

H86 then measures the same budget curve on the exact H80 finite value score
instead of the ideal H85 tail. This is the first really useful response-surface
shape:

```text
margin 0.216226 bits -> delta needed 0.005205 bits
margin 0.229195 bits -> delta needed 0.005870 bits
margin 1.000000 bits -> delta needed 0.148322 bits
```

The named soft law from H84 also looks better as a fertility investment than a
hard support class:

```text
H84 R0.90:  delta=1.158938, lift=2.962770, lift-delta=1.803832
hard top25: delta=2.000000, lift=3.093383, lift-delta=1.093383
```

That does **not** make `R0.90` a recursive compressor: H84 already shows the
invariant `R->R` current-layer saving is exactly zero. The useful reading is
more specific. Soft high-entropy output laws are a better target than hard
valid/fertile subsets. The missing mechanism is now:

```text
a fixed, stateless Telomere record language whose native emitted bytes follow
a high-ROI soft value-tail law without a stored profile, hidden selector, or
paid reshaping ledger.
```

H87 prices the repeatable-cycle version of that target. If a native grammar
can keep the next layer `P`-shaped, the source-shaped cycle margin can be
positive. But starting from arbitrary uniform data must also pay the
uniform-to-`P` capacity bill:

```text
startup_shape_bill = n * (n / H(P) - 1)
```

The tiny threshold rows cancel:

```text
H58 threshold: delta=0.005579, shape=0.005581, startup=-0.005581
H7 threshold:  delta=0.210348, shape=0.214101, startup=-0.214101
```

Strong soft laws still show positive source-shaped margins, e.g.
`delta=1.158938` gives `startup H58=1.450744`, but only if the H80 score lift
becomes actual second-pass Telomere witness savings. That is now the live
proof obligation.

H88 tests the parseability part directly with a frozen public type-class
grammar. For public `theta` and block length `m`, the type counts are fixed,
so no profile selector is stored. Small `m` collapses the soft law into a hard
support class, but large public blocks recover the soft grammar:

```text
theta=1.05, m=32768:
  bill=1.734528, lift=3.295267, eta=1.560740, top25=0.797302

best m<=512:
  eta=-0.328511
```

This means the "native parseable grammar" objection is not the current blocker
in the toy domain; a frozen grammar can pay its own finite overhead. The
remaining blocker is whether `V=log2(Q/U)` is merely a score or becomes real
selected-record savings under exact Telomere witness accounting.

H89 performs that hard check by replacing the score with actual best-cover
record savings:

```text
paid_saving(x) = raw_bits - best_cover_cost(x)
```

On the same exact H80/H74 domain:

```text
E_U paid_saving:          -5.022461
E_Q paid_saving:          -1.005994
positive-saving fraction:  0.029541
```

The `Q` score is genuinely aligned with better witnesses, but not enough:

```text
best finite score-law:
  theta=1.34, m=32768, cycle=-2.530640

best finite oracle-saving law:
  theta=1.04, m=32768, cycle=-2.397156

shuffled savings at best score-law:
  avg_cycle=-7.384625, max_cycle=-6.853363
```

So H88's positive `eta` was a value-score margin, not verified compression.
The next target is now sharper again: a native law whose value function is
actual witness-cost reduction, or a mechanism that closes about `2.4` bits/word
in this toy without hiding a selector/profile.

H90 proves that this is not fixable by a better public tilt over the same
witness family. For a witness weight `w(x)=2^-cost(x)` and saving:

```text
S(x) = log2(M) + log2 w(x)
```

the exact variational identity is:

```text
E_P[S] - D(P||U) = log2 Z - D(P || w/Z)
```

where `Z=sum_x w(x)`. Therefore:

```text
sup_P [E_P[S] - D(P||U)] = log2 Z
```

H89's exact domain gives:

```text
best selected:    Z=0.221606134, log2 Z=-2.173930
all descriptions: Z=0.676912187, log2 Z=-0.562959
```

So selected best-cover witnesses cannot be rescued by source shaping, and even
the collective all-description witness family is still below the line.

H91 turns that no-go into a target budget by asking how much honest Kraft mass
would make `Z` cross `1`:

```text
family             flat bits/word  bits/record
best selected      2.173930        1.086792
all descriptions   0.562959        0.277599
```

That is the current sharpest constructive target: the collective/all-description
route is only about `0.28` honest bits per record short in the toy domain.
Any proposed breakthrough must identify where those bits come from and show
they are not paid back as delimiters, profile selectors, birth/pass ledgers,
final-board coordinates, or rare-tail losses.

H92 then tests the user's obvious frontier knob directly: increase `K` and `D`.
In the optimistic H74 extended-arity lower bound, collective rows do cross:

```text
best lower-bound collective:
  K=8, D=12, log2 Z_total=1.001339
```

But H92's `K>5` rows use:

```text
ceil(log2(K)) + payload_width
```

which omits J3D1 witness-width metadata. H93 reruns the same finite `K/D`
sweep with paid extended arity:

```text
K<=5: exact V1 record_cost_for_payload_width
K>5:  ceil(log2(K)) + J3D1(seed_payload_width)
```

All crossings disappear:

```text
best paid selected:    K=12, D=12, log2 Z_best=-6.054405
best paid collective:  K=12, D=12, log2 Z_total=-5.301885
```

So higher arity/deeper search is a real frontier mover only under an underpriced
witness-width oracle in this toy. Under paid Lotus accounting, `K/D` alone does
not break the witness Kraft wall.

H94 tests the middle ground between H92 and H93: a custom arithmetic witness
language that normalizes the rank or whole record distribution instead of paying
full J3D1. It reruns the same finite `K/D` grid with four modes:

```text
h92_lower:    K<=5 exact V1; K>5 fixed arity bits + payload_width
custom_rank:  fixed arity bits + arithmetic-coded normalized rank
custom_record: arithmetic-coded normalized (arity, rank) record
paid_lotus:   K<=5 exact V1; K>5 fixed arity bits + J3D1(payload_width)
```

Only the underpriced lower bound crosses:

```text
mode           best collective row        log2 Z_total
h92_lower     K=8, D=12                   1.001339
custom_rank   K=8, D=10                  -2.188694
custom_record K=6, D=12                  -1.781751
paid_lotus    K=12, D=12                 -5.301885
```

So H92 was not merely missing a clever arithmetic coder. Once the rank or
record universe is normalized, the width-class multiplicity becomes a paid
channel and the crossing disappears. The next live route must change the
generated span law, create real neutral/developmental fertility, or add a paid
public invariant that increases honest witness Kraft mass.

H95 then tests the most direct "biology-like generator" variant: keep the paid
V1 total-cover record language fixed, but bias the public seed expander toward
local spans that are easier to cover again. This does create shape:

```text
law                   log2 Z     U excess   top25   future lift
uniform            -11.885765   0.274471   0.2167  -0.1991
fertile theta=0.5  -11.885765   0.400053   0.3218   0.2996
fertile theta=2.0  -11.885765   1.592915   0.3410   0.6671
```

But the whole-cover Kraft mass is conserved. The generator law changes which
strings receive mass; it does not create more paid descriptions. For the
normalized public law `Q(x)=Q_raw(x)/Z`, even the ideal matching source cycle has:

```text
source_saving - source_bill = log2 Z
```

So fixed native bias is a useful source-shaped/developmental mechanism only if a
real public source law or recurrence invariant supplies the shape. It is not the
missing arbitrary-content channel by itself.

H96 tests the strongest biology-shaped variant left after H95: visible neutral
genotypes. A concrete paid record string is the genotype, its decoded word is
the phenotype, and its next-pass all-description compressibility is fertility.
The encoder may choose among synonymous descriptions, but the chosen bits are
the output, so no neutral-rank selector is hidden.

In the exact tiny domain:

```text
B=1,N=5,K=3,D=3
avg descriptions/word            1636.000
E_U best transfer cycle          -60.307024
E neutral future lift             +5.659472
E future lift vs posterior        +6.719114
Pr cycle positive                  0.000000
```

This is the cleanest split so far. Neutral genotype choice really can steer
future fertility: the selected visible record strings are much better than
random same-length strings on the next pass. But the visible record strings are
paid in the current pass, and the paid two-pass cycle remains deeply negative
in the exact enumeration. Therefore neutral transfer survives only as a
source-shaped/developmental target, not as a roughly-all-data escape.

H97 scales H96 with sampled visible-genotype search and stricter controls. It
keeps the same legal move: the chosen genotype bits are emitted, so no decoder
selector is stored. But it adds posterior one-draw, conservative `log2(m)` net,
and best-of-same-budget random same-length controls:

```text
name                 cycle      logm net   future    randM    liftM
h96_anchor_sampled  -60.307    -66.990   -43.870   -39.170  -4.699
small_deeper        -57.594    -65.253   -42.828   -35.895  -6.933
mid_v1              -47.198    -55.763   -31.370   -27.585  -3.784
v1_frontier_probe   -39.502    -48.214   -24.705   -20.149  -4.556
```

The sampled cycles improve as `N/K/D` grow, but remain negative. More
importantly, the same-budget random controls beat the selected genotypes in
every row. So H97 downgrades the current neutral-transfer signal from "maybe a
native grammar" to "ordinary best-of-visible-string search" until a real public
interpreter or recurrent fertility law is added.

H98 reopens the user's partial slack-refresh story directly. It allows
`+0/+1/+2/+4` bit records and asks whether replacing enough atoms can keep
future targets fresh without requiring total cover. The kernel reports three
prices: unpaid carry, an H2 ready/carry lower bound, and a stateless literal
rewrite lower bound.

```text
best unpaid:
  v1_B8_K5, slack=0, budget=0.00
  mean log2 rho=-0.000706
  final fresh fraction=0.000000

best unpaid with >=10% fresh output:
  xarity_B4_K32, slack=4, budget=0.05
  mean log2 rho=+0.014129

best H2-charged lower bound:
  v1_B8_K5, slack=0, budget=0.00
  mean log2 rho=+0.007534

best stateless literal rewrite:
  v1_B8_K5, slack=4
  mean log2 rho=+0.346924
```

So the lattice effect is real but split: tiny unpaid shrinkage appears only
when freshness dies; maintained freshness expands; and even the generous
binary ready/carry lower bound removes the gain. This is exactly the kind of
place another agent could have seen "success" by leaving the carry state off
the bill.

H110 sharpens H98 by computing a one-pass Pareto frontier: for each possible
rewritten fraction `q`, find the cheapest selected interval cover, then add the
optimistic binary ready/carry lower bound `N*H2(q)`.

```text
best parseable J3D1 q>=10%:
  B4_K128_D512, slack=8
  H2 delta=+0.524497 bits/atom

best parseable J3D1 q>=50%:
  B4_K128_D512, slack=8
  H2 delta=+0.653950 bits/atom

best local-width oracle q>=10%:
  B4_K16_D64, slack=4
  H2 delta=-0.111979 bits/atom

best zero-arity oracle q>=50%:
  B8_K32_D256, slack=2
  H2 delta=-1.472656 bits/atom
```

This is a useful positive signal but not a codec: the local-width oracle hides
the payload boundary. J3D1 makes the witness parseable and spends the option
dividend. So the partial-refresh lane's live target is now narrower:

```text
derive payload width/boundary from a public invariant
or code the width stream collectively below J3D1
while still paying ready/carry layout
```

H111 tests exactly that collective-width target by separating the arity stream,
width/delta stream, and payload stream. The result narrows the bill again:

```text
mode              config          slack  qmin  delta bits/atom
local oracle      B4_K16_D64      4      .10   -0.118750
fixed delta       B4_K128_D512    8      .10   +0.127344
enum counts-free  B4_K16_D64      4      .10   -0.073289
enum count-paid   B4_K128_D512    8      .10   +0.147041
J3D1              B4_K128_D512    8      .10   +0.168652
```

Collective width coding improves the J3D1 bill, but only the counts-free
version crosses. Once the per-file delta histogram/count vector is charged,
the row is still positive. The next concrete partial-refresh target is
therefore a frozen public width/delta law that beats the universal count bill
on held-out rows without a file-specific profile.

H112 tests that frozen public width/delta law in the ordinary H2-charged
partial-refresh branch. It does not cross:

```text
B4_K16_D64, slack=4, qmin=.10
global held-out              +0.2531 bits/atom
arity_bucket held-out        +0.2907 bits/atom
target_arity_bucket held-out +0.3163 bits/atom
```

So a public delta law alone does not replace the H111 per-file histogram while
the H2 ready/carry map is still present.

H113 then combines the user's seed-class readiness idea with the partial
refresh Pareto DP. Visible parity is charged by widening the seed witness; it
is allowed to replace H2 only under a forced two-epoch invariant:

```text
current records use class t mod 2
old records use class t-1 mod 2
old records must refresh or literalize before parity repeats
```

The best paid fixed-delta parity row becomes a narrow miss:

```text
B4_K32_D128, slack=2, q>=0.50
fixedD + parity 2-epoch = +0.023438 bits/atom
local + parity 2-epoch  = negative
```

Static many-pass parity still fails: with 64 live epochs, one parity bit leaves
five residual age bits/record, or exact 64-class birth marking costs six seed
class bits/record.

H114 is the first paid partial-refresh target that crosses in this run. It
keeps H113's visible two-epoch parity readiness and replaces fixed-delta width
syntax with a frozen public `P(delta | context)` trained on independent
uniform-law covers:

```text
B4_K32_D128, slack=4, context=global
default held-out delta = -0.020876 bits/atom
q ~= 0.555
records/atom ~= 0.0417
avg arity ~= 13.75
```

Focused repeat:

```text
train/eval = 32/64
seed 114114 -> -0.013144 bits/atom
seed 214114 -> -0.008421 bits/atom
seed 314114 -> -0.009607 bits/atom
seed 414114 -> -0.004403 bits/atom
```

This is not promoted as a finished file format. It is a paid custom target with
load-bearing conditions: extended arity, parseable record-layer input, frozen
public delta law, visible class bit paid in witness width, and mandatory
old-cohort refresh/literalization. The next proof obligation is an exact
two-epoch codec/accounting model that charges literal/bootstrap records and
proves sequential parse without a hidden cover-shape channel.

H115 performs that first record-layer audit. Items are variable-length stream
objects with bit length, represented raw length, and age. The decisive mode is
`force_refresh`: age-1 records cannot be skipped; every due old record must be
covered by a new record before parity aliases.

One-pass calibration still finds a small lower-bound crossing:

```text
H114_raw_lower, P=1, global:
  -0.005424 bits/atom
```

But the four-pass due-refresh row goes positive:

```text
H114_raw_lower, force_refresh, global:
  +0.020909 bits/atom/pass

H114_raw_lower, no_expiry lower bound:
  -0.014058 bits/atom/pass
```

The negative `no_expiry` row is invalid because it lets old records survive
past the parity alias. Literal expiry is also positive in the raw lower-bound
config. Removing the visible class bit through an optimistic public-lane/local
class row does not rescue the frozen law in the focused check:

```text
public_lane_raw, force_refresh, global:
  +0.011262 bits/atom/pass
```

The branch is not dead, though: with the same due-refresh geometry, a local
payload-width oracle remains negative:

```text
H114_raw_lower, local oracle, force_refresh:
  -0.047175 bits/atom/pass

public_lane_raw, local oracle, force_refresh:
  -0.085214 bits/atom/pass
```

So H115 downgrades H114 from "paid crossing target" to "fixed-atom lower-bound
crossing." The live target became more precise: forced due-cohort refresh over
heterogeneous item lengths needed a better frozen public width law, or a public
lane/local-class grammar whose membership was truly derivable and whose
force-refresh row was negative.

H116 tests that next target directly. It keeps the H115 forced-refresh
transition and changes only the frozen width-law context. Public contexts use
only arity, output-item index modulo a public period, and scheduled lane counts.
Hidden diagnostic contexts use target length or actual age/literal interval
composition before the decoder could know them.

Quick 96-atom public rows all stay positive:

```text
H114_raw_lower, global:          +0.031077 bits/atom/pass
H114_raw_lower, arity:           +0.008734 bits/atom/pass, fail 0.25
H114_raw_lower, start_mod_arity: +0.021417 bits/atom/pass
H114_raw_lower, lane_due_arity:  +0.010648 bits/atom/pass
```

The hidden diagnostics do not rescue this bucketed language either:

```text
H114_raw_lower, target_lane_arity hidden:
  +0.009967 bits/atom/pass, fail 0.25

public_lane_raw, target_lane_arity hidden:
  +0.011742 bits/atom/pass
```

Focused 128-atom repeats remain positive:

```text
H114_raw_lower, arity public:
  +0.023659 bits/atom/pass, fail 0.25

public_lane_raw, target_lane_arity hidden:
  +0.021842 bits/atom/pass, fail 0.125
```

That makes H116 a miss, but a useful one: the missing channel is not solved by
a simple public arity/lane clock, and even bucketed hidden target/age facts are
too weak in this witness language. The next target should change the witness
family itself, such as a collective record-layer stream, or make interval
composition public through a real lane/board invariant and charge the placement
supply loss.

H117 corrects one more parser assumption in the H114-H116 line. A delta symbol
is parseable for fixed atoms because `target_bits = arity * B` is known from
the arity. In a heterogeneous record stream, the decoder usually does not know
`target_bits` before reading the seed payload, so H117 codes payload width
itself:

```text
[arity][payload-width symbol][payload bits]
```

The honest width stream is near-flat only when sparse:

```text
H114_raw_lower, lane_due_arity, width symbol, 128 atoms:
  +0.007218 bits/atom/pass
  rewrite_frac 0.124268
```

When the row is forced to rewrite enough raw material to plausibly maintain
fresh match pressure, it expands hard:

```text
min_rewrite_raw_frac=0.25:
  +0.061297 bits/atom/pass

min_rewrite_raw_frac=0.50:
  no finite path in the small sweep
```

So H117 does not produce a codec either. It does, however, sharpen the target:
future due-refresh rows must either code payload width parseably at meaningful
refresh density, or make target-size class public through a priced board/lane
invariant. "Cheap delta" cannot be used for variable-length records unless the
target length channel is explicitly present and charged.

H118 tests the obvious amortization follow-up: code selected payload widths
collectively over a pass. It uses the H117 local-width oracle cover and then
prices the selected width sequence as fixed-width, count-free enumerative,
exact count-paid enumerative, and scaled/asymptotic enumerative streams.

At scale 1, count-free enumeration appears to cross:

```text
H114_raw_lower, min_rewrite=0.25, enum_free scale 1:
  -0.005928 bits/atom/pass
  width_bits/record 1.376490
```

But this is a short-sequence artifact, not a large-file amortized win. Scaling
the same empirical pass ledger makes the width-stream rate approach its entropy:

```text
enum_free scale 1024:
  +0.025875 bits/atom/pass
  width_bits/record 2.256638

enum_count_paid scale 1024:
  +0.026359 bits/atom/pass
  width_bits/record 2.270043
```

So the count header is not the only missing bill. The selected width sequence
itself carries about `2.26` bits/record in this lower-bound row, enough to spend
the local-oracle margin. The next target is now even sharper: reduce actual
selected-width entropy, make width nearly deterministic from public geometry,
or change the witness language so payload boundaries self-synchronize without
that width channel.

H119 tests the most direct public-geometry version of that target: do not encode
width at all; make payload width a frozen public function `W(context)` of arity,
lane phase, or start modulo:

```text
[arity][fixed W(context) payload bits]
```

Sparse global rows can look slightly negative:

```text
H114_raw_lower, global, q=0.90:
  -0.003906 bits/atom/pass
  rewrite_frac 0.037760
```

But this is a low-refresh artifact. With `min_rewrite_raw_frac=0.25`, the rows
fail or expand:

```text
H114_raw_lower, exact_arity, q=0.50:
  +0.408854 bits/atom/pass, fail 0.75

public_lane_raw, lane_exact_arity, q=0.90:
  +0.020833 bits/atom/pass, fail 0.75

H114_raw_lower, target_exact_arity hidden, q=0.90:
  +0.023438 bits/atom/pass, fail 0.75
```

So fixed public width lanes do not solve H118. They remove width entropy only
by paying padding and match-supply loss. The hidden target-size row missing is
the key tell: this family is too blunt even when given information that a real
decoder would not have for free.

H120 performs the requested closure audit for "hide the width elsewhere." It
prices the exact same selected width sequence as explicit width bits,
seed-class supply loss, self-synchronizing prefix syntax, and checksum/referee
ambiguity.

With the H118 seed:

```text
scale 1024:
  enum/record                  5.337140
  count_paid/record            5.345849
  entropy/record               5.341012
  seed_class/record            5.341012
  checksum64_records          11.991442
```

So these are not different currencies. A seed class that makes width derivable
pays `H(W)`. A self-sync grammar has the same lower bound. A checksum can
referee only a finite number of width decisions, about 12 here before any
safety margin. H120 also corrects the optimistic H118 reading: the `~2.26`
bits/record figure was a per-ledger lower bound; pooled independent selected
widths are closer to `5.3-5.6` bits/record.

H121 tests Herschel's stronger public geometry: a typed board where target
length is public, so payload width is a fixed public gap:

```text
W = T_pub - G
record = [arity][W payload bits]
```

The kernel gives the board the hard part for free by setting `T_pub` equal to
the actual interval bit length. Even under that optimistic lower bound:

```text
min_rewrite_raw_frac=0.25:
  gaps 1..16 all fail

min_rewrite_raw_frac=0.10, H114_raw_lower, gap 4:
  +0.007812 bits/atom/pass
  supply_loss 2.892468 bits

min_rewrite_raw_frac=0.10, public_lane_raw, gap 5:
  0.000000 bits/atom/pass
  fail 0.500
```

So public target length plus a fixed gap is not enough. Small gaps keep supply
but lack savings; large gaps save per hit but lose due-refresh coverage.

H122 tests the next middle ground: a small public gap alphabet. The decoder
reads a paid gap class, then derives `W = T_pub - gap`. This is still an
optimistic typed-board lower bound because `T_pub` is set to the actual interval
length.

At `min_rewrite_raw_frac=0.25`, the regular H114 rows miss:

```text
H114_raw_lower, gaps 4,5,6,8:
  +0.005469 bits/atom/pass
  fail 0.843750

H114_raw_lower, gaps 4,6,8,10:
  0.000000 bits/atom/pass
  fail 0.843750
```

The class-bit-free public-lane lower bound can make finite rows negative, but
only by failing most trials:

```text
public_lane_raw, gaps 4,5,6,8:
  -0.002686 bits/atom/pass
  fail 0.750000

public_lane_raw, gaps 4,6,8,10:
  -0.015625 bits/atom/pass
  fail 0.843750
```

Wider alphabets reduce failure but give the margin back:

```text
public_lane_raw, gaps 1,2,3,4,5,6,8,10:
  +0.001674 bits/atom/pass
  fail 0.125000
```

This is a close lower-bound miss, but not a codec: maintained refresh needs zero
stale exceptions. The next target is therefore no longer "add more gap choices";
it is making gap choice predictable from public geometry or changing the search
objective so selected intervals naturally concentrate in a low-entropy,
high-saving gap class.

H123 freezes the gap choice into a public table `G(context)` instead of paying
a per-record gap selector. This improves the lower bound but still fails often:

```text
public_lane_raw, exact_arity, q=0.10:
  -0.006460 bits/atom/pass
  fail 0.593750

public_lane_raw, lane_exact_arity, q=0.10:
  -0.010851 bits/atom/pass
  fail 0.437500
```

H124 repairs those failures by letting stale due records expire. Raw fallback
keeps the finite lower-bound row negative, but only while hiding the output
type stream:

```text
public_lane_raw, exact_arity, expire_raw_atoms:
  delta/atom/pass        -0.014587
  type bitmap/atom/pass  +0.157235
  type runs/atom/pass    +0.261375

public_lane_raw, lane_exact_arity, expire_raw_atoms:
  delta/atom/pass        -0.023438
  type bitmap/atom/pass  +0.193945
  type runs/atom/pass    +0.303097
```

Literal fallback is honest but expands (`+0.115234` and `+0.074870`
bits/atom/pass on the same two rows). The lower-bound win is therefore an
adaptive raw/record placement channel, not maintained stateless compression.

H125 and H126 test the obvious public geometries for that channel. Fixed public
raw lanes/runs are parseable but fail the meaningful `25%` rewrite rows,
including `period=8, raw_run=7`. One/two raw segments are more flexible but
still expand before the boundary bill at `atoms=128`; exact segment boundaries
add `0.08-0.15` bits/atom/pass, far above the H124 margin.

H127 directly tests the proposed partial-rewrite sweet spot. From `1%` through
`25%` rewrite, raw lower-bound rows remain negative, but the repaired rows stay
positive:

```text
public_lane_raw, exact_arity:
  raw delta/pass   -0.012858 to -0.016764
  bitmap net/pass  +0.142941 to +0.147396

public_lane_raw, lane_exact_arity:
  raw delta/pass   -0.019206 to -0.025391
  bitmap net/pass  +0.152125 to +0.167864
```

H128 quantifies the only remaining order-insensitive public-board shape. If the
exception ledger is `H2(eps)+eps*log2(P-1)`, the measured H124 margins require
roughly `99.77%-99.94%` public opening as `P` grows from `2` to `4096` passes.
This is not impossible as a mathematical target, but it is a very narrow box.

H129 tests counted stable-partition zones where each fixed zone parses as
`[raw prefix][record suffix]` and pays one raw count. This also misses:

```text
public_lane_raw, exact_arity, zone=32, min_rewrite=0.25:
  +0.121578 bits/atom/pass
  count ledger +0.097489
  fail 0.250000

public_lane_raw, exact_arity, zone=128, min_rewrite=0.25:
  fail 1.000000
```

The raw-fallback family therefore needs a public rule that derives the raw
counts/positions essentially for free; ordinary count ledgers, bitmaps, fixed
lanes, and small segment lists all cost more than the refresh margin.

H130 combines the near-total exception ledger with the witness-margin target.
It shows that exceptions are not an easier path than all-open; they strictly
raise the paid witness boost required:

```text
H105 custom_record:
  all-open boost needed:
    0.468557 bits/record

  eps=0.001, P=4096, F=0:
    0.542498 bits/record

  eps=0.001, P=4096, F=3:
    0.551974 bits/record
```

So the clean target remains all-open public geometry plus positive paid
forced-rewrite witness margin. Near-total exceptions are only a fallback when
all-open cover cannot be guaranteed.

H131 tests the stronger typed all-open public board proposed by the independent
audit: arity, width/target class, seed class, salt, and placement are all public
slot facts, so only witness payload remains. That solves parsing, but the
finite-capacity law is severe. If the previous layer has `N` bits and the board
stores `W=N-G` witness bits, then expected per-pass coverage is
`1-exp(-2^-G)`. Saving one bit covers only `39.35%` of arbitrary layers per
pass; `90%` final survival over `4096` passes requires about `3.40` bits of
bloat. A typed all-open board is therefore decode geometry, not a uniform
compression source, unless a public recursive fertility law makes the next
layers non-uniform under the board's `Q`.

H132 tests the user's partial-refresh sweet spot as a paid self-consistent
width-law problem: let the selector allow small bloat, require meaningful
rewrite, charge `-log2 P(width | context)` during selection, refit from selected
covers, freeze the law, then evaluate held-out. It misses:

```text
public_lane_raw, lane_due_arity, atoms=128, passes=4:
  +0.041360 bits/atom/pass
  4.105557 width bits/record
  fail 0.500000

public_lane_raw, arity, atoms=64, passes=3:
  +0.024703 bits/atom/pass
  2.758183 width bits/record
  fail 0.000000

public_lane_raw, target_arity hidden diagnostic, atoms=64, passes=3:
  +0.017235 bits/atom/pass
  2.374375 width bits/record
  fail 0.000000
```

So the refresh lattice is real, but this frozen paid width law does not make it
compressive. The next move cannot be merely "choose the best +1/+2 bloat cover";
it needs a witness family or public invariant that actually lowers held-out
selected-width entropy.

H133 tests common-cause batch witnesses: one base witness derives several child
witnesses, hoping to amortize record boundaries. Under the uniform hash law, the
honest batch mass is the m-fold convolution of the base record mass. Exact H108
recurrence shows valid batches do not improve the H105 target:

```text
base custom_record:
  log2 symbol mass = 0.000000
  log2 Z_N = -1.781751

batch_only m=2:
  log2 symbol mass = 0.000000
  log2 Z_N = -2.897549

batch_only m=3:
  log2 symbol mass = 0.000000
  log2 Z_N = -2.993887

best valid base/batch mixture:
  log2 Z_N = -1.781751
```

The positive-looking rows are exactly overfull:

```text
discounted_batch m=2, discount=2:
  log2 symbol mass = 2.000000
  log2 Z_N = 1.220990
  valid = false
```

So common-cause batching is not a free witness-boundary escape unless it brings
a real joint/fertility law. Independent child seeds collapse to higher arity or
an overfull-code artifact.

H134 tests CRT/modular readiness clocks, including even/odd and
Fibonacci/Zeckendorf-style registers. A residue vector modulo `m_i` can
distinguish at most `lcm(m_i)` epochs while costing `log2(prod m_i)` seed-supply
bits. The sweep confirms the floor:

```text
P=2:
  moduli (2,)
  cost 1.000000 bits

P=64:
  moduli (5,13)
  cost 6.022368 bits

P=4096:
  moduli (8,19,27)
  cost 12.002815 bits
```

Thus CRT clocks can be efficient, but only equal to an ordinary pass tag in the
best case. They help stateless decode only after a separate invariant bounds
record lifetime, e.g. the H99/H100 two-epoch forced-refresh geometry.

H135 starts the exact recurrent transfer-operator harness suggested by the
fertility branch. It applies a frozen public rule:

```text
T_lambda(x) = argmax_c [len(x)-len(c) + lambda*fertility(c)]
```

where `c` is the visible next layer and `fertility(c)` is actual
all-description next-pass saving. The first bounded exact control is not a
crossing:

```text
B=1,N=3,K=1,D=1,max_bits=16,passes=2:
  lambda 0 and 1 both fail 1.000000
  no zero-failure recurrent row
```

Richer exact rows became expensive quickly because pass two targets visible
record strings rather than tiny raw words. H135 is therefore a harness and a
support-failure warning, not a closure of the fertility idea. A future positive
would need a native visible language or transfer-matrix formulation that keeps
support while charging visible length exactly.

H136 tests the stronger final-board/egg-carton batch-footprint idea over an
uncovered mask. It gives each footprint an optimistic normalized witness-rank
mass of `1`, so only footprint geometry is under test. Valid public/paid
footprint grammars reach at most zero margin:

```text
interval_normalized K=6:
  log2 Z = 0.000000
  valid = true

all_masks_normalized K=4:
  log2 Z = 0.000000
  valid = true

all_masks_ceil K=4:
  log2 Z = -0.377551
  valid = true
```

The crossing rows are exactly unpaid footprint selectors:

```text
all_masks_free K=4:
  log2 Z = 21.656226
  max local mass log2 = 7.857981
  valid = false
```

So egg-carton footprints remain useful decode geometry, but not a compression
source under the uniform law. The missing margin must come from a witness family
or fertility law, not from free footprint choice.

H137 tests the closed-loop bits-back salt flywheel. Posterior tape can make
salting stateless if reverse decode order is canonical and final tape is
settled, but the tape is conserved:

```text
P=64, gap=0.250, tape=64, salt=64, gamma=1:
  net = -16.000

P=4096, gap=0.250, tape=64, salt=64, gamma=1:
  net = -1024.000
```

Unbalanced tape is worse because final/initial state must be visible:

```text
P=64, gap=0, tape=64, salt=8:
  final settlement = 3584 bits
  net = -3584
```

The only positive rows require `gamma>1`, a real fertility/source law where a
salt bit creates more than one bit of future paid witness margin. Bits-back is
therefore a strong salting implementation scaffold, not the missing compression
source.

H138 tests bounded reset ratchets. A reset bounds damage, but the final saving
after `P` recursive passes is controlled by the good suffix after the last
reset. Representative results:

```text
P=4096, eps=0.01, s=1:
  expected suffix = 99.000 good passes
  net/pass = -0.005830
  half-rate probability = 0.000000

P=4096, eps=0.001, s=1:
  expected suffix = 982.412 good passes
  net/pass = 0.236847
  half-rate probability = 0.128861

P=4096, eps=0.0001, s=1:
  expected suffix = 3360.642 good passes
  net/pass = 0.820169
  half-rate probability = 0.814802
```

For half-rate `90%` survival, reset probability must scale like `O(1/P)`:

```text
P=64       eps <= 0.00328710173
P=4096     eps <= 0.000051444241
P=1000000  eps <= 0.000000210721
```

So reset ratchets are bounded-loss engineering, not a maintained compression
source, unless another mechanism already makes reset probability vanish with
pass count.

H139 adds the stricter reset/ratchet converse ledger. Any claim of `S` saved
bits over a high-coverage family must face the short-output support bound:

```text
P64_s1_c90:
  S = 64 bits
  prefix coverage bound = 5.421e-20
  eps max for 90% survival = 0.0016449
  loser expansion needed = 576 bits

P64_s1_c90_state64:
  visible state bits = 64
  charged saving = 0

P64_s1_c90_hidden2^32:
  apparent hidden bound = 2.328e-10
  paid hidden bound = 5.421e-20
```

So visible state cancels claimed saving, finite hidden best-of choice cancels
when the selector is paid, and many-pass survival still requires reset
probability to shrink like `O(1/P)`.

H140 reopens the user's `+1/+2` partial-refresh story as a supply calculation.
For a central atom, the kernel counts all interval placements containing that
atom:

```text
lambda = sum_k k * Pr(length-k interval has a slack-legal seed)
q      = 1 - exp(-lambda)
```

The good news is that the option-pressure argument is real in the underpriced
local-width oracle:

```text
local_width_oracle, B=4,K=5,slack=0: q = 0.894601
local_width_oracle, B=4,K=5,slack=2: q = 0.999877
```

The paid result is narrower:

```text
j3d1_parseable, B=4,K=32,slack=0:
  q = 0.101126
  H2(q)/q = 4.672923 bits per rewritten atom

j3d1_parseable, B=4,K=32,slack=2:
  q = 0.342932
  H2(q)/q = 2.704901 bits per rewritten atom

j3d1_parseable, B=4,K=32,slack=4:
  q = 0.800679
  H2(q)/q = 0.899946 bits per rewritten atom
```

With exact J3D1 and `D=K*B`, `B=4,slack=2` reaches `q>=0.10` at `K=5` but
does not reach `q>=0.50` by `K=4096`; `slack=4` reaches `q>=0.50` at `K=5`
but not `q>=0.90` by `K=4096`. This explains the earlier H110 split: the
local-width lattice has enough option pressure, but the decoder-visible
payload-boundary/width syntax and partial-cover ready/carry layout consume the
dividend.

H141 tests the natural follow-up: make the seed witness itself carry the
boundary by residue, trailing pattern, parity/sign lane, canonical minimum, or
self-delimiting seed language. The converse is Kraft:

```text
sum_witness 2^(-len(witness)) <= 1
```

For a fixed record delta, the best possible seed-derived boundary supply is a
public fixed-width witness lane at the best arity. Representative rows:

```text
B=4,K=32,delta=-1:
  q = 0.393469
  partial+H2 = +0.954706 bits/atom
  fixed-slot literal fallback = +0.044566 bits/atom

B=4,K=32,delta=0:
  q = 0.632121
  partial+H2 = +0.949030 bits/atom
  fixed-slot literal fallback = +0.034489 bits/atom

B=4,K=32,delta=2:
  q = 0.981684
  partial+H2 = +0.193231 bits/atom
  fixed-slot literal fallback = +0.063072 bits/atom
```

So compressive seed-derived boundary records are too sparse, flat records fail
too often, and near-total freshness requires bloating records. The seed language
can make boundaries parseable, but it cannot restore the overfull local-width
oracle.

H142 optimizes the intrinsic-boundary channel directly. Using the H120 pooled
ledger:

```text
local-width oracle delta = -0.055664 bits/atom/pass
selected rate            =  0.036133 records/atom/pass
measured H(W)            =  5.341012 bits/record
break-even H(W)          =  1.540537 bits/record
```

The optimal seed-class/Kraft construction costs exactly `H(W)`, so the honest
intrinsic-boundary row remains positive:

```text
optimal Kraft loss = 5.341012 bits/record
total              = +0.137322 bits/atom/pass
```

Even cutting the width entropy in half still misses:

```text
hypothetical H(W) = 2.670506 bits/record
total             = +0.040829 bits/atom/pass
```

Terminator/self-sync schemes are ordinary prefix languages (`0^4`, length 32
costs `6.310489` bits of seed inventory; `0^5`, length 64 costs `7.356225`).
Neutral multiplicity discounts class loss only when expected matches are
already large (`lambda=16,class=1/2` gives `0.000484` bits), which is the flat
or bloating high-supply regime rather than a compressive rare-match regime.

H143 combines near-total public-board geometry with exact J3D1 opening supply.
It is intentionally generous: each atom may use the cheapest successful public
interval containing it, and no cover-conflict or winner-selector cost is
charged. Even then:

```text
B4,K32,slack=2:
  q = 0.342931792
  expected record delta = +0.029757626 bits/atom

H124 lane apparent, P=4096:
  required q = 0.998998607
  best q for slack<=2 = 0.342931792
```

Large slack can reach near-total opening only by bloating:

```text
B4,K128,slack=8:
  q = 1.000000000
  total delta at P=4096,F=0 = +0.032630302 bits/atom
```

So public board geometry solves decode status but not compression under the
current exact witness law.

H144 then reopens the user's non-greedy/superposition idea in the right
currency. The question is not whether the chosen seed is smallest now, but
whether its future paid value beats its current bloat. Under an optimistic
exponential future-value model:

```text
E[max future value among M candidates] = mu * E[H_M]
```

The easiest rows to rescue are the high-multiplicity slack-8 rows:

```text
B4,K128,slack=8:
  current delta = +0.032630 bits/atom
  E[H_M] = 3.783020
  mu_required = 0.008625 bits/atom/candidate

B4,K512,slack=8,P=4096:
  current delta = +0.097450 bits/atom
  mu_required = 0.040116 bits/atom/candidate
```

This is a real target, not a solution. A codec must now measure actual
recurrent future value for selected same-budget seeds against random controls.
If the value is iid noise, the best-of lift is not a stable fertility law.

H145 prices the deeper "seed unfolds through larger states and later shrinks"
intuition. A fixed public depth gives one output per seed. A stop among `T`
intermediate states gives `T` descriptions, but the stop time costs `log2(T)`
or an equivalent checksum/referee channel:

```text
90% coverage with G saved bits:
  required steps ~= 2^G * 2.302585
  stop bits = G + 1.203254
  net if stop stored = -1.203254 bits

G=16:
  required 90% steps = 150902.216654
  stop bits = 17.203254
```

So upward unfolding is a compute-for-compression target only if a public
invariant derives the stop depth, or if it feeds the H144 measured-fertility
route.

H146 tests that H144 route in the smallest exact visible-genotype kernel. For
each starting word it enumerates every paid V1/J3D1 record-string description
within a slack budget, then compares cheapest-now against a two-pass public
lookahead rule. The selected record string is the only output; discarded
alternatives are not stored.

The signal exists but is not yet enough:

```text
N=5,K=5,D=8,slack=10:
  coverage = 1.000000
  two-pass total = -19.570534 bits/word
  future-vs-random = -0.089661 bits

N=6,K=5,D=7,slack=14:
  coverage = 1.000000
  two-pass total = -29.390338 bits/word
  lift over cheapest-now = +0.141632 bits/word
  future-vs-random = +0.621127 bits
```

So non-greedy slack is not a metadata hack, and it can select more fertile
visible genotypes. But in the exact tested family, current bloat dominates.
The next version must replace the collective next-pass score with an actual
selected recurrent record stream and beat same-budget random controls by the
H144 target amount.

H147 then isolates the larger-intermediate intuition from stop/referee
channels. If decode depth/path is fixed and stateless, the whole upward/downward
route collapses to one final description string. Intermediate length does not
appear in the capacity bound:

```text
32-bit targets, exact final length n-G:
  G=8  coverage <= 0.003906
  G=16 coverage <= 1.526e-05
```

Letting a final seed try `T` hidden branches or stop depths raises coverage, but
the branch selector costs `log2(T)`:

```text
90% coverage, exact final length:
  branch bits = G + 1.203254
  net = -1.203254 bits
```

Thus upward detours remain a valid search strategy, but not an extra stateless
address space. The live target is a public fertility invariant that makes the
good branch derivable, or a visible record language whose selected strings
carry that fertility directly.

H148 replaces H146's collective next-pass score with an actual selected
two-pass stream:

```text
x --pass 1--> c1 --pass 2--> c2
```

Both arrows are paid visible record-string descriptions, and the final stored
stream is `c2`. In the default exact support check:

```text
N=4,K=4,D=7,slack=8:
  pass1 coverage = 0.937500
  two-pass coverage = 0.000000

N=4,K=4,D=7,slack=12:
  pass1 coverage = 1.000000
  two-pass coverage = 0.000000
```

So the stricter selected-stream model does not even preserve support in this
small family. That does not close non-greedy transfer; it says the next tool
should be a bounded recurrent transfer matrix/DP, not wider brute enumeration
over visible second-pass strings.

H149 builds that next tool at the decode-composition level. It enumerates every
valid final top-layer stream in a tiny fixed public language, composes the
decoder for `P` passes, and counts bottom strings reached by a shorter final
stream. There is no stop depth, branch selector, or intermediate side channel.

Default high-arity toy:

```text
B=1,K=16,D=4,stream_cap=18,output_cap=24:
  valid top streams = 476

P=1,n=16,saved=4:
  reachable outputs = 13
  coverage = 0.000198

P=2:
  composed streams = 3
  reachable outputs at n=1..16,saved=1 = 0

P=3:
  composed streams = 0
```

Wider toy:

```text
B=1,K=32,D=3,stream_cap=20,output_cap=40:
  valid top streams = 980
  P=2 composed streams = 1
  reachable outputs at n=16,24,32 = 0
```

So the fixed-depth non-greedy route is now pinned to a sharper missing piece:
self-parse closure. A final top-layer address can unfold upward only if the
intermediate layer lands back in the record language often enough to keep
decoding. Making that closure public/forced is the next target; otherwise the
missing branch/stop/repair choice is a paid channel.

H150 implements the selected-stream transfer DP suggested by the H148/H149
failure. It keeps an online min-plus parser state for the generated
intermediate layer:

```text
state = (t, hlen, tail, f[0..K])
```

where `f[0]` is the cheapest actual selected second-pass final stream length.
This removes H146's collective future-score optimism without brute-forcing all
second-pass strings.

Default reproduction:

```text
N=4,K=4,D=7,slack=12:
  pass1 coverage = 1.000000
  pass2 selected coverage = 0.000000
```

Looser slack buys support but not compression:

```text
N=4,K=4,D=7,slack=20:
  pass2 coverage = 0.625000
  mean final length = 29.100000 bits
  mean gain = -25.100000 bits/word

N=5,K=4,D=7,slack=20:
  pass1 coverage = 1.000000
  pass2 selected coverage = 0.000000
```

The non-greedy/superposition route is therefore still live only as a closure
problem: make the visible intermediate language cheaply re-encodable by the
same public grammar, and price the support restriction or shaping cost.

H151 prices the simplest closure repair directly: require generated
intermediates to be valid record streams. For a fixed public grammar:

```text
closure_tax(t) = -log2(#valid_record_streams_of_length_t / 2^t)
```

This tax is paid as lost match supply, not as wire metadata.

Representative rows:

```text
B1,K4,D7:
  record Kraft mass = 0.129180908
  t=12 density = 0.023438
  closure tax = 5.415037 bits

B1,K5,D8:
  t=12 density = 0.027344
  closure tax = 5.192645 bits

B1,K16,D4:
  t=9/11/12 closure tax = 5.000000 bits
  t=8/10/16 have zero valid streams

B4,K128,D16:
  t=24 closure tax = 5.912537 bits
  t=64 closure tax = 10.019899 bits
```

So closure by subset restriction is much too expensive relative to H144's
`0.008625-0.040116` bits/atom/candidate rescue target. A literal or
prefix-complete repair can make support easy, but then the final selected
stream pays raw/literal length and H150's support-by-bloat behavior returns.

H152 then separates the user's non-greedy/superposition idea from hidden branch
mass. It enumerates visible intermediates `c` where `c -> x`, then compares the
greedy shortest `c`, the non-greedy `c` whose cheapest final stream `y -> c` is
shortest, and the whole unselected future-description cloud.

Representative rows:

```text
N4,K4,D7,slack12:
  selected coverage = 1.000000
  visible non-greedy lift = 0.375000 bits
  mean explicit final stream = 31.187500 bits for 4 input bits
  cloud gap = 6.612638 bits

N6,K5,D7,slack18:
  selected coverage = 1.000000
  visible non-greedy lift = 1.890625 bits
  non-greedy intermediate fraction = 0.406250
  mean explicit final stream = 41.593750 bits for 6 input bits
  cloud gap = 7.868868 bits
```

So the non-greedy objection is correct: greedy immediate shrinking wastes
visible option value. But the larger superposition/cloud gain is not a free
stateless channel. A decoder sees one final stream, not the discarded cloud;
using that whole cloud requires a paid rank/arithmetic distribution or a public
source law. The next target is therefore a visible recurrent grammar where the
selected-stream lift scales faster than the explicit final witness cost.

H153 makes that last sentence exact by turning the H152 cloud into a public
arithmetic distribution:

```text
Q(x) = q_raw(x) / sum_x q_raw(x)
E_U[-log2 Q(X)] = n + KL(U || Q)
```

Focused rows:

```text
N4,K4,D7,slack12:
  normalized Q cross entropy = 6.126916 bits
  Q excess over raw = +2.126916 bits
  best raw/Q alpha = 0

N6,K5,D7,slack18:
  normalized Q cross entropy = 7.456567 bits
  Q excess over raw = +1.456567 bits
  cloud gap = 7.868868 bits
  best raw/Q alpha = 0
```

So the cloud can be honest only as a source-shaped public-Q codec, a paid
rank/arithmetic stream, or a search diagnostic for visible selected-stream
fertility. Under the roughly-all uniform branch, normalizing the cloud pays
`KL(U||Q)` and the raw/Q mixture falls back to raw.

H154 tests the opposite closure tactic: make every output unit a fixed-size
record cell, so every next layer parses for free. A `C`-bit cell carries:

```text
[ceil(log2 K) arity bits][C-ceil(log2 K) seed bits]
```

The match probability for an arity-`a` interval is:

```text
p_a = 1 - (1 - 2^(-a*C))^(2^W)
```

Focused grid rows:

```text
C4,K5:
  lambda = 0.138285
  touched per cell ~= 0.129149
  expected untouched cells in 128 = 111.468915
  full-cover success = 0

C8,K128:
  lambda = 0.007859
  expected untouched cells in 128 = 126.998037
```

So fixed cells solve parseability but spend the seed-address budget. The
dominant arity-1 coverage is about `2^-ceil(log2 K)`, and higher arities are
exponentially rarer by `2^-C` per added cell. Free closure plus one-cell records
therefore starves match rate instead of maintaining it.

H155 stacks the closest constructive pieces as a cross-domain target ledger,
without charging open/carry/birth entropy:

```text
public two-epoch lanes + class-local ranks + non-greedy selected-stream lift
```

The key base-only row is:

```text
H105 custom_record K6,D12:
  base gap = 1.781751 bits/word
  missing = 0.468557 bits/record
  implied records/word = 3.802635

H152 N6,K5,D7,slack18:
  visible non-greedy lift = 1.890625 bits/H152-word
  selected gain = -35.593750 bits/word
  cloud gap = 7.868868 bits

base_after_lift = -0.108874 bits/word
```

That is the clearest positive signal in the public-lane branch: measured
visible non-greedy lift is numerically large enough, as a target-transfer
magnitude, to cover the H105 base collective witness miss. It is not an
observed combined-codec crossing. The same row does not solve recursion:

```text
H151 closure stress at the rounded intermediate length = 8.733213 bits
closure_after_lift = +8.624339 bits/word

H120 width stress bill = 5.341012 bits/record
width_after_lift = +20.201047 bits/word

best stacked row after closure+width stress = +22.798591 bits/word
```

These are stress columns, not exact debits on H152's selected `y -> c -> x`
row. They name the bills a future closed public-lane mechanism must internalize,
make public, or pay. The next target is sharply defined: preserve H152-style
visible lift while making width and closure public/parseable by construction,
without paying for that construction by destroying seed address space as in
H154. The H152 cloud is not credited because H153 priced it as KL loss or a
hidden rank stream.

H156 tests the obvious completion repair for that closure stress. Start with a
seed-record grammar of Kraft mass `K_R`, then add filler/literal codewords using
the remaining leaves:

```text
K_R + K_F = 1
```

For each exact stream length:

```text
seed_closure_tax = completed_parse_tax + seed_preservation_tax
```

Representative rows:

```text
B1_K16_D4, t=13:
  seed closure tax = 7.415037 bits
  completed parse tax = 0.142019 bits
  seed preservation tax = 7.273018 bits
  expected filler fraction = 0.993534

B1_K4_D7, t=16:
  seed closure tax = 10.607683 bits
  completed parse tax = 0.198494 bits
  seed preservation tax = 10.409189 bits
  expected filler fraction = 0.998635

B4_K32_D16, t=28:
  seed closure tax = 7.999868 bits
  completed parse tax = 0.500154 bits
  seed preservation tax = 7.499714 bits
  expected filler fraction = 0.989010
```

Completion therefore makes streams parse mostly by making them filler. If
filler is literal/raw repair, freshness is lost and visible raw length is paid;
if every next-layer record must stay seed-bearing, the preservation tax restores
the H151 seed-only closure bill. Together with H106/H108, the three ledgers are:

```text
syntax Kraft: K_R + K_F <= 1
cover mass:   Z_n = sum_a S_a Z_{n-a} <= 1 for valid seed records
closure:      tau(t) = -log2(valid_streams_t / 2^t)
```

Completion helps the syntax ledger, not the uniform source-free cover margin.

H157 replaces cloud/filler scoring with an exact recursive selected-stream DP.
Every layer is seed-bearing, and lower passes may bundle across upper-record
boundaries. The bounded caps are explicit:

```text
mid_cap   = maximum visible size of any generated intermediate layer
final_cap = maximum visible size of the final stored stream
```

Representative rows:

```text
N4,K4,D4,P1,mid24,final56:
  coverage = 1.000000
  mean final bits = 13.437500
  mean gain = -9.437500

N4,K4,D4,P2,mid24,final56:
  coverage = 1.000000
  mean final bits = 39.187500
  mean gain = -35.187500

N3,K3,D3,P3,mid40,final256:
  coverage = 0.375000
  mean final bits = 117.000000
  mean gain = -114.000000
```

So lawful non-greedy recursion exists as a parser object, but the tested closed
seed-bearing language still expands. More selected depth raises visible final
length much faster than it creates compression.

H158 instruments the current SPEC-style keep-what-decodes referee in the Robin
proof model. It counts distinct terminal outputs before checksum, not just DFS
paths:

```text
N4,T4,rep0:
  final records = 4
  pre-checksum paths = 180
  distinct pre-checksum outputs = 180
  checksum-winning outputs = 1
  log2(outputs) = 7.491853 bits

N6,T4,rep1:
  final records = 4
  pre-checksum paths = 84
  distinct pre-checksum outputs = 22
  checksum-winning outputs = 1
  log2(outputs) = 4.459432 bits
```

The checksum proves correctness in these finite rows, but it is a finite
referee. To be an unbounded stateless opening channel, a future proof must show
`log2(pre-checksum outputs)` stays bounded, or the growing referee bits must be
paid explicitly.

H159 builds the corrected seed-bearing closed-core graph. Nodes are visible
H96 seed-record streams. An edge exists only when the source is an actual
bounded H96 description of the full visible target stream:

```text
y -> x  iff  y decodes to visible seed-record stream x
```

This is the record-to-record closure test, not the narrower raw
`record.value` test. The important columns are:

```text
srcTax   = -log2(source_mass / valid_node_mass)
shortF   = fraction of nodes with any shorter predecessor
shortTax = -log2(shorter_predecessor_target_mass / valid_node_mass)
sccN     = nodes inside nontrivial recurrent SCCs
bestG    = max(len(target)-len(source)) over edges
```

Representative rows:

```text
K2,D2,cap24:
  nodes = 152
  edges = 0
  sccN = 0
  shortF = 0

K4,D3,cap24:
  nodes = 1499
  edges = 7
  srcTax = 12.874046 bits
  sccN = 0
  shortF = 0
  bestG = -11 bits

K5,D3,cap28:
  nodes = 21387
  edges = 283
  srcTax = 11.895128 bits
  sccN = 0
  shortF = 0
  bestG = -11 bits
```

No recurrent seed-bearing SCC appears, and no node has a shorter predecessor.
The few closed descriptions are one-way and length-expanding. This does not
prove no such language can exist; it does kill this exact H96 closed-core
variant. The stronger next version is a prefix-safe transfer matrix/product
automaton so closure mass is counted without relying on finite enumeration.

H160 implements that transfer-matrix count for the same H96 surrogate. Source
streams are H96 records; emitted target bits are accepted only if the target
parser is back at a seed-record boundary. It matches H159's finite closed-edge
counts:

```text
K4,D3,cap24:
  H159 edges = 7
  H160 closed paths = 7

K4,D3,cap28:
  H159 edges = 127
  H160 closed paths = 127

K5,D3,cap28:
  H159 edges = 283
  H160 closed paths = 283
```

The mass ledger is harsher:

```text
K4,D3,cap24:
  clFrac = 0.000131
  clTax = 12.900937 bits
  compressive closed paths = 0
  bestG = -11

K4,D3,cap28:
  clFrac = 0.000145
  clTax = 12.755488 bits
  compressive closed paths = 0
  bestG = -11

K5,D3,cap28:
  clFrac = 0.000258
  clTax = 11.918435 bits
  compressive closed paths = 0
  bestG = -11
```

The structural reason is visible in the `min(c-a)` column: every source record
costs more visible bits than it emits as target bits. In this bit-level H96
surrogate, a source stream therefore cannot be shorter than its emitted target
bitstream. The closed-core branch must move to an item-level grammar, where a
record emits self-delimiting items rather than raw bits, before it can be a
serious maintained-compression candidate.

H161 makes that move to SPEC-style item targets. The model is still analytic
under the uniform hash law: target items are literals and/or records, a source
record of arity `a` expands to exactly `a` target items, and candidate sources
are grouped by exact J3D1 record cost. It reports both the conditioned item
grammar view and the unconditioned mass view, so a rare valid syntax island is
not allowed to masquerade as file-level compression.

The strict maintained-freshness row is `seed_only`, because literals do not
refresh future seed-match opportunities. The best tested strict arity-2 row is:

```text
B8,K5,D80,seed_only,a2:
  seqK = 0.245625
  seqTax = 2.025472 bits
  hitMass = 0.179325
  accMass = 0.000276
  saveMass = 0.000577
```

This is the first recent closed-language branch that shows a real local
opportunity again: item-level closure lets a short record target multiple
self-delimiting record items whose visible length can exceed the source cost.
But it is not yet a solution. The accepted compressive mass is only `0.000276`,
and the attractive `save|seq` numbers are conditioned on the current stream
already being valid seed-item syntax. `mixed_all` looks stronger
(`D40,a2 saveMass = 0.000991`) but spends literals, which weakens the maintained
freshness invariant.

The next non-greedy kernel is therefore not another one-record probe. It is a
full-cover item-stream DP: given a current public item stream, choose
non-overlapping source records over `1..K` target items, charge exact record
costs, and measure whether expected per-item drift goes negative. That is the
right place to test slack replacement, alternate witness selection, and
superposition-style "not best now, maybe fertile later" rules without hiding
the selector or closure cost.

H162 runs that exact current-format DP for V1/J3D1 `K=5`. It samples current
item streams from the normalized public item-grammar mass, samples interval
match availability and best source cost from the analytic uniform hash law, and
then lets a min-cost DP choose the full non-overlapping cover. No greedy
first-found rule is being used.

The strict `seed_only` rows still miss:

```text
B8,K5,D80,N16:
  support = 0.585
  gain/item = -4.189423

B8,K5,D80,N32:
  support = 0.310
  gain/item = -4.110081
```

`mixed_all` is slightly less bad but spends literals:

```text
B8,K5,D80,N32,mixed_all:
  support = 0.384
  gain/item = -3.472168
```

So the H161 local signal was not a reward hack, but it is not enough. Once the
whole current item stream must be covered by actual matching source records,
the successful covers still expand by several bits per item and many streams
have no full cover. The next priced knobs are: an extended arity grammar with
its exact Kraft cost, a custom total-cover item witness language, a genuinely
source-shaped/fertile item distribution, or a repair channel whose price is
lower than the H162 miss.

H99 prices seed parity/rejection as a readiness channel. Seed classes are legal:
pass `t` may use class `t mod C`, and the decoder can read the class from the
seed witness. But accepting only one class costs `log2(C)` bits of match supply.

```text
P live  g  C   paid  2-bit net  exact?
2       1  2   1.0   +1.0       true
4       2  4   2.0    0.0       true
64      1  2   6.0   -4.0       false
64      6  64  6.0   -4.0       true
```

Even/odd seeds are therefore a paid two-epoch discriminator, not a free
many-pass birth channel. The idea remains useful for bounded near-total
exception designs, where only one old/current distinction is live. It does not
solve recursive stateless decoding across many live passes by itself.

H100 turns that opening into the forced two-epoch target. If max record lifetime
is `<=1` pass, then birth age is only current/previous and parity is injective:

```text
pass t births only class t mod 2
decoder opens class t mod 2
decoder carries class t-1 mod 2 exactly once
```

The target formula is:

```text
r = selected records per input atom
m = base paid margin before seed-class restriction, bits/record
q = fraction of output record slots born/refreshed this pass
c = seed-class bits

net_bits_per_atom = q * r * (m - c)
```

For even/odd parity, `c=1`, so the base mechanism must supply more than `1`
paid bit/record before parity can be positive. Current rows fail:

```text
H7 current parity net:   -0.020716 bits/atom
H9 current parity net:   -0.022079 bits/atom
H12 upper parity net:    -0.019183 bits/atom
```

A hypothetical real `+2` bits/record mechanism would survive the stateless
readiness layer:

```text
H9-density, q=1.00: +0.009765 bits/atom
H9-density, q=0.90: +0.008788 bits/atom
```

The residual age entropy table catches the aliasing problem:

```text
L=2,c=1    -> H(age | age mod C)=0
L=64,c=1   -> H(age | age mod C)=5 bits/record
```

Two read-only subagents converged on the same verdict: forced two-epoch public
lanes/seed classes are real stateless decode geometry, but only if an
enforcement invariant refreshes or literalizes the previous cohort before it
ages again. A ready-prefix boundary alone does not pay arbitrary membership;
content-selected prefix membership still costs `log2 C(N,R)`.

H101 checks the obvious discount: if a selected witness bucket contains many
neutral matching seeds, maybe choosing the even/odd class costs less than a full
bit. The Poisson class ledger is:

```text
lambda = 2^(witness_width - target_bits)
p_all = 1 - exp(-lambda)
p_class = 1 - exp(-lambda / 2^c)
class_loss = -log2(p_class / p_all)
```

That discount is real, but it is paid for by wider/slacker witness buckets:

```text
best discounted parity row:
  slack=1
  class_loss=0.830905 bits/record
  base margin=-1.449341 bits/record
  net=-0.027835 bits/atom

cheapest parity class row:
  slack=-12
  class_loss=0.260736 bits/record
  base margin=-5.346307 bits/record
  net=-0.057494 bits/atom
```

So H100's target should be read as `base margin > class_loss after width/slack
accounting`, not necessarily `base margin > 1`. In the tested H9 fixed-slack
frontier, the discounted class loss still does not cross.

H102 finds a cleaner way to separate readiness from seed supply. If the class is
carried by a public lane/position, the witness can be a local rank inside the
class-specific seed enumerator:

```text
seed = G[class].seed_at(local_rank)
```

Then `W` witness bits name `2^W` seeds inside the public class. There is no
one-bit visible-parity supply loss. The bill moves to the lane invariant:

```text
public lane + local grammar:
  positive iff base margin > 0

content-selected lane + local grammar:
  positive iff base margin > H(q)/q

visible global seed class:
  positive iff base margin > class_loss
```

Current paid rows still fail because their base margins are negative:

```text
H7 public-lane q=1:  -0.011927 bits/atom
H9 public-lane q=1:  -0.012314 bits/atom
H12 public-lane q=1: -0.008196 bits/atom
```

But the target is meaningfully narrower. A hypothetical `+0.28` bits/record
collective witness mechanism would be positive under public lane local grammar:

```text
hyp +0.28, q=1:
  visible global parity -> -0.007200 bits/atom
  public local grammar  -> +0.002800 bits/atom
```

This makes the best surviving spec shape:

```text
public two-epoch lanes
+ class-local seed enumeration
+ mandatory old-cohort refresh/literalization
+ separate paid witness mechanism with base margin > 0
```

The class channel is not free in arbitrary layouts. H102's counting sanity keeps
the anti-reward-hack line: at `N=1,000,000,R/N=0.50`, a boundary costs
`0.000040` bits/open but arbitrary subset membership costs `1.999979`
bits/open. The lane must be public, or the subset must be paid.

H103 checks H102 in the exact H74/H94 finite Kraft domain. It compares the base
rank grammar, visible global seed class restriction, and local class grammar:

```text
family                 K   D   collective log2Z   delta vs base
base_all               6   8        -1.781751       0.000000
visible_global_class   6   8        -5.464267      -3.682516
local_class            6   8        -1.781751       0.000000

base_all               8  10        -2.188694       0.000000
visible_global_class   8  10        -5.115053      -2.926359
local_class            8  10        -2.188694       0.000000
```

So local class grammar is not hidden Kraft mass. It preserves the base family
when the lane supplies the class; visible parity loses mass because the seed
witness is carrying readiness. That makes the remaining blocker more precise:
not birth/open entropy, but positive paid forced-rewrite witness margin.

H104 audits the current `SPEC_V1` keep-what-decodes claim against scaling. The
small proof artifacts are valid finite decodes (`robins_opening_rules.py`
`12/12`, `v1_roundtrip_proof.py` `36/36`), but they do not prove the survivor
set stays bounded for arbitrary files and passes. Caveat: `v1_roundtrip_proof.py`
is supplementary, not the exact current position-salt architecture, because it
uses pass salts for bundles and original-slot salts for singles. In the
arity-1 carried-record worst case:

```text
S = T^R readings before checksum
referee bits = R * log2(T)
```

The finite capacity table is sharp:

```text
T=64:
  64-bit checksum covers R <= 10.667 independent carried records
  with 32 safety bits, covers R <= 5.333 records

T=256:
  64-bit checksum covers R <= 8.000 records
  with 32 safety bits, covers R <= 4.000 records
```

So position salt is self-presenting for the correct birth reverse step, but
trial decoding still needs either a bounded survivor set or a referee whose
effective bits grow with `R log2 T`. This is not a new impossibility claim; it
is the current spec's own open scaling bill made explicit. The surviving
stateless paths are therefore unchanged:

```text
total-cover/all-open
public two-epoch lanes with mandatory refresh
near-total exceptions with the exception ledger paid
or a new invariant that bounds survivor readings independently of record count
```

H105 combines the surviving pieces into the strict forced-rewrite collective
target. In exact `B=1,N=12` H74/H94 accounting:

```text
mode            K   D   log2 total   public    visible+1  eps001
h92_lower       8  12     1.001339   0.000000  1.000000   0.000000
custom_rank     8  10    -2.188694   0.692022  1.692022   0.752763
custom_record   6  12    -1.781751   0.468557  1.468557   0.520646
paid_lotus     12  12    -5.301885   2.233401  3.233401   2.287744
```

The public-lane/class-local correction is meaningful: it removes about
`1` bit/record of readiness tax compared with visible global parity. But the
nearest honest row still misses. The constructive target is now as sharp as:

```text
q=1 forced rewrite
+ public two-epoch lanes
+ class-local seed ranks
+ collective witness family with paid log2Z_total > 0
```

The nearest current toy target is `custom_record K=6,D=12`, requiring
`0.468557` honest bits/record of real witness-margin/Kraft boost.

H106 asks whether that H105 gap is just bad public arity weighting. It reduces
the whole-cover grammar to:

```text
F_0 = 1
F_n = sum_a W_a F_{n-a}
sum_a W_a <= 1  for a valid uniquely parseable record grammar
```

Thus `F_n <= 1` by induction. The exact rows:

```text
N   K   equal log2F   best valid divisor   random max
12  6   -1.781751     0.000000             -0.492237
12  8   -2.188694     0.000000             -0.833908
24  6   -1.807942     0.000000             -0.473271
```

The H105 `custom_record K=6,D=12` miss is exactly the equal-arity
`K=6,N=12` recurrence. Reweighting arity mass can make a fixed-length grammar
complete (`log2Z=0`) by concentrating mass on an arity that tiles `N`, but it
cannot make the forced-rewrite row positive. Positive mass appears only with
invalid total record mass:

```text
sum W_a=1.10 -> log2F_N=0.275007, but Kraft is violated
```

So the missing `0.468557` bits/record cannot come from ordinary public
arity/rank allocation. The remaining margin must come from an invalid
underpriced code, a named non-uniform source law, a paid visible invariant, or
a genuinely new syntax that is not equivalent to concatenated record symbols.

H107 checks the adjacent biased-seed-grammar route. Holding the same arity
masses `W_a=1/K` for `K=6,N=12,B=1`, it changes only the public value law:

```text
shape            log2Z       reach   CE excess   best alpha   mix excess
uniform_values  -1.781751    1.000   0.000000    0.00         0.000000
zero_attractor  -1.781751    0.000   inf         0.00         0.000000
half_fertile    -1.781751    0.473   inf         0.00         0.000000
random_lumpy    -1.781751    1.000   0.162096    0.00         0.000000
```

So value shaping changes which strings are favored but not total witness mass.
Under the uniform roughly-all-data premise, normalized `Q` does not beat raw on
average; the raw/`Q` mixture falls back to raw. Biased seed grammars therefore
remain source-shaped/fertility-cycle candidates, not content-blind margin.

H108 turns the prefix-record converse into an exact `Fraction` audit for the
H94/H105 modes:

```text
mode           K   D    log2 symbol mass   log2 Z_N    valid?
h92_lower      8  12       2.055381         1.001339   false
custom_rank    8  10       0.000000        -2.188694   true
custom_record  6  12       0.000000        -1.781751   true
paid_lotus    12  12      -1.607617        -5.301885   true
```

So the H92 crossing is mechanically an overfull-code artifact, while the
nearest honest H105 row is exactly a valid subprobability family. This is the
cleanest anti-reward-hack audit for the collective-witness lane so far.

H109 prices the remaining "let the decoder try readings and keep the checksum
winner" route. For a non-prefix length language:

```text
A_0 = 1
A_m = sum_{l in L,l<=m} A_{m-l}
referee liability = log2 max_{j<=m} A_j
```

The exact kernel uses the prefix maximum because exact-length ambiguity is not
monotone. A fixed 64-bit referee buys only a finite ambiguous window:

```text
language       lengths                   rate bits/bit     m@64    m@64-32safe
fixed8         (8,)                           0.000000  unbounded      unbounded
fib_1_2        (1, 2)                         0.694242         92             46
byte_or_marker (8, 9)                         0.117788        569            296
record_7_16    (7, 16)                        0.092059        730            382
lotus_toy      (7..16)                        0.312208        215            113
```

For carried records this is the same old ledger:

```text
S = T^R
log2 S = R * log2(T)
```

So non-prefix syntax/checksum pruning remains a legitimate bounded engineering
tool, but it is not an unbounded birth/open channel unless a separate public
invariant keeps survivor readings bounded independently of file size and pass
count.

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
`P2-biased-hash_coupling_ledger.py`, `P2-recursion-ledger.py`,
`H2-uniform_counting_boundary.py`, `H3-bundle_finite_k_ledger.py`,
`H4-cover_layout_entropy.py`, `H5-total_cover_split_ledger.py`,
`H6-total_cover_suffix_partition.py`, `H7-total_cover_parametric_delta.py`,
`H8-total_cover_objective_beta.py`, `H9-total_cover_fixed_slack.py`,
`H10-total_cover_tail_schedule.py`, `H11-total_cover_order_stat_delta.py`,
`H12-neutral_fertility_capacity.py`, `H13-joint_selected_cover_partition.py`,
`H14-public_crf_cover_partition.py`, `H15-recursive_counting_converse.py`,
`H16-prior_escape_ledger.py`, `H18-developmental_fertility_threshold.py`,
`H19-neutral_ecology_tree_kernel.py`, `H21-positional_geometry_ledger.py`,
`H22-phase_lane_total_cover_hybrid.py`,
`H24-active_lane_total_cover.py`,
`H25-global_referee_amortization.py`,
`H26-value_count_separation.py`,
`H27-orderless_confluence_ledger.py`,
`H28-public_fertility_class.py`,
`H29-cover_equivalence_dp.py`,
`H30-public_dither_refresh.py`,
`H31-coset_syndrome_ledger.py`,
`H32-bits_back_reservoir.py`,
`H33-debruijn_universal_tape.py`,
`H34-xor_fountain_superposition.py`,
`H35-confluent_normal_form.py`,
`H36-developmental_attractor_basin.py`,
`H37-d_choice_router.py`,
`H38-combined_fertility_lane_threshold.py`,
`H39-two_layer_fertility_source.py`,
`H40-eof_length_code.py`,
`H41-position_ready_compaction.py`,
`H42-response_surface_map.py`,
`H43-forced_rewrite_target_surface.py`,
`H44-normalized_collective_cover.py`,
`H45-neutral_selection_fertility.py`,
`H46-option_statistic_bound.py`,
`H47-public_residual_law.py`,
`H48-seed_grammar_arity.py`,
`H49-all_block_rg_kernel.py`,
`H50-rg_sweep.py`,
`H51-normalized_q_rg.py`,
`H52-fixed_slack_percolation_rg.py`,
`H53-global_slack_ladder.py`,
`H54-selector_referee_budget.py`,
`H55-unique_slack_survivor_audit.py`,
`H56-self_sync_slack_ladder_rg.py`,
`H57-normalized_q_percolation_rg.py`,
`H58-frozen_q_arity_model_rg.py`,
`H59-raw_q_stop_mixture.py`,
`H60-recursive_shrink_converse.py`,
`H61-scientific_phase_diagram.py`,
`H62-source_fertility_phase.py`,
`H63-recursive_fertility_invariant.py`,
`H64-repeatable_nonprefix_path_ledger.py`,
`H65-public_invariant_exhaustion.py`,
`H66-all_block_cover_entropy_bound.py`,
`H67_typical_drift_rare_blowup.py`,
`H68-public_code_martingale_audit.py`,
`H69-rank_width_sampling_bias.py`,
`H70-systematic_response_protocol.py`,
`H71-finite_pass_coverage_frontier.py`,
`H72-public_q_visible_state_converse.py`,
`H73-final_state_entropy_kernel.py`,
`H74-exact_latent_q_kernel.py`,
`H75-rare_blowup_coverage_ledger.py`,
`H76-randomized_codebook_ledger.py`,
`H77-self_induced_fertility_kernel.py`,
`H78-master_no_go_audit.py`,
`H79-d_choice_fertility_conservation.py`,
`H80-public_q_fertility_lane.py`,
`H81-output_whitening_fertility.py`,
`H82-syntax_support_capacity.py`,
`H83-length_preserving_relabeling.py`,
`H84-graded_native_law.py`,
`H85-entropy_budget_fertility.py`,
`H86-native_value_tail_audit.py`,
`H87-native_soft_cycle_ledger.py`,
`H88-frozen_soft_grammar_overhead.py`,
`H89-actual_witness_savings.py`,
`H90-witness_kraft_variational_bound.py`,
`H91-witness_kraft_boost_budget.py`,
`H92-kd_witness_kraft_sweep.py`,
`H93-kd_paid_lotus_sweep.py`,
`H94-normalized_rank_witness_sweep.py`,
`H95-biased_expander_conservation.py`,
`H96-neutral_transfer_operator.py`,
`H97-sampled_neutral_transfer_sweep.py`,
`H98-partial_slack_refresh_kernel.py`,
`H99-seed_parity_readiness_ledger.py`,
`H100-two_epoch_parity_exception_ledger.py`,
`H101-neutral_parity_discount.py`,
`H102-public_lane_local_class_grammar.py`,
`H103-class_local_kraft_check.py`,
`H104-spec_decode_scaling_audit.py`,
`H105-forced_rewrite_collective_target.py`,
`H106-cover_sequence_kraft_capacity.py`,
`H107-value_shape_conservation.py`,
`H108-prefix_record_grammar_converse.py`,
`H109-nonprefix_referee_capacity.py`,
`H110-partial_refresh_pareto.py`,
`H111-collective_width_stream.py`,
`H112-frozen_width_delta_law.py`,
`H113-seed_class_partial_refresh.py`,
`H114-frozen_delta_parity_refresh.py`,
`H115-two_epoch_record_layer.py`,
`H116-public_width_law_search.py`,
`H117-parseable_width_symbol.py`,
`H118-collective_width_amortization.py`,
`H119-public_fixed_width_lanes.py`,
`H120-width_channel_equivalence.py`,
`H121-public_gap_typed_board.py`,
`H122-public_gap_alphabet.py`,
`H123-public_gap_table.py`,
`H124-gap_table_fallback_repair.py`,
`H125-public_raw_lane_repair.py`,
`H126-raw_segment_boundary.py`,
`H127-type_priced_refresh_sweep.py`,
`H128-near_total_exception_threshold.py`,
`H129-zone_prefix_raw_counts.py`,
`H130-near_total_witness_margin.py`,
`H131-typed_all_open_board_capacity.py`,
`H132-self_consistent_width_selection.py`,
`H133-common_cause_batch_witness.py`,
`H134-modular_clock_readiness.py`,
`H135-recurrent_transfer_operator.py`,
`H136-batch_footprint_mask_dp.py`,
`H137-bits_back_salt_flywheel.py`,
`H138-bounded_reset_ratchet.py`,
`H139-reset_ratchet_converse.py`,
`H140-slack_refresh_supply_bound.py`,
`H141-kraft_boundary_converse.py`,
`H142-intrinsic_boundary_optimizer.py`,
`H143-near_total_public_board_bound.py`,
`H144-non_greedy_lookahead_value.py`,
`H145-unfold_depth_stop_ledger.py`,
`H146-slack_superposition_transfer.py`,
`H147-upward_detour_collapse.py`,
`H148-two_pass_selected_stream.py`,
`H149-decode_composition_capacity.py`,
`H150-selected_stream_dp.py`,
`H151-closure_kraft_ledger.py`,
`H152-superposition_gap_ledger.py`,
`H153-cloud_q_conservation.py`,
`H154-fixed_cell_closure_phase.py`,
`H155-closed_lane_nongreedy_target.py`,
`H156-completion_seed_mass_tradeoff.py`,
`H157-recursive_selected_stream_dp.py`,
`H158-opening_referee_scaling.py`,
`H159-seed_bearing_closed_core.py`,
`H160-seed_closure_transfer_matrix.py`,
`H161-item_level_closure_economics.py`,
`H162-item_stream_cover_dp.py`,
`findings/H17-original-goal-audit.md`,
`findings/H18-developmental-fertility-threshold.md`,
`findings/H19-neutral-ecology-tree-kernel.md`,
`findings/H20-cover-equivalence-arithmetic.md`,
`findings/H21-positional-decode-geometry.md`,
`findings/H22-phase-lane-total-cover-hybrid.md`,
`findings/H23-final-board-coordinate-decode.md`,
`findings/H24-active-lane-total-cover.md`,
`findings/H25-global-referee-amortization.md`,
`findings/H26-value-count-separation.md`,
`findings/H27-orderless-confluence.md`,
`findings/H28-public-fertility-class.md`,
`findings/H29-cover-equivalence-dp.md`,
`findings/H30-public-dither-refresh.md`,
`findings/H31-coset-syndrome-ledger.md`,
`findings/H32-bits-back-reservoir.md`,
`findings/H33-debruijn-universal-tape.md`,
`findings/H34-xor-fountain-superposition.md`,
`findings/H35-confluent-normal-form.md`,
`findings/H36-developmental-attractor-basin.md`,
`findings/H37-d-choice-router.md`,
`findings/H38-combined-fertility-lane-threshold.md`,
`findings/H39-two-layer-fertility-source.md`,
`findings/H40-eof-length-code.md`,
`findings/H41-position-ready-compaction.md`,
`findings/H42-response-surface-map.md`,
`findings/H43-forced-rewrite-target-surface.md`,
`findings/H44-normalized-collective-cover.md`,
`findings/H45-neutral-selection-fertility.md`,
`findings/H46-option-statistic-bound.md`,
`findings/H47-public-residual-law.md`,
`findings/H48-seed-grammar-arity.md`,
`findings/H49-all-block-rg-kernel.md`,
`findings/H50-rg-sweep.md`,
`findings/H51-normalized-q-rg.md`,
`findings/H52-fixed-slack-percolation-rg.md`,
`findings/H53-global-slack-ladder.md`,
`findings/H54-selector-referee-budget.md`,
`findings/H55-H56-self-sync-slack-syntax.md`,
`findings/H57-normalized-q-percolation-rg.md`,
`findings/H58-frozen-q-arity-model.md`,
`findings/H59-raw-q-stop-mixture.md`,
`findings/H60-recursive-shrink-converse.md`,
`findings/H61-scientific-phase-diagram.md`,
`findings/H62-source-fertility-phase.md`,
`findings/H63-recursive-fertility-invariant.md`,
`findings/H64-repeatable-nonprefix-path-ledger.md`,
`findings/H65-public-invariant-exhaustion.md`,
`findings/H66-all-block-cover-entropy-bound.md`,
`findings/H67-typical-drift-rare-blowup.md`,
`findings/H68-public-code-martingale-audit.md`,
`findings/H69-rank-width-sampling-bias.md`,
`findings/H70-systematic-response-protocol.md`,
`findings/H71-finite-pass-coverage-frontier.md`,
`findings/H72-public-q-visible-state-converse.md`,
`findings/H73-final-state-entropy-kernel.md`,
`findings/H74-exact-latent-q-kernel.md`,
`findings/H75-rare-blowup-coverage-ledger.md`,
`findings/H76-randomized-codebook-ledger.md`,
`findings/H77-self-induced-fertility.md`,
`findings/H78-master-no-go-audit.md`,
`findings/H79-d-choice-fertility-conservation.md`,
`findings/H80-public-q-fertility-lane.md`,
`findings/H81-output-whitening-fertility.md`,
`findings/H82-syntax-support-capacity.md`,
`findings/H83-length-preserving-relabeling.md`,
`findings/H84-graded-native-law.md`,
`findings/H85-entropy-budget-fertility.md`,
`findings/H86-native-value-tail-audit.md`,
`findings/H87-native-soft-cycle-ledger.md`,
`findings/H88-frozen-soft-grammar-overhead.md`,
`findings/H89-actual-witness-savings.md`,
`findings/H90-witness-kraft-variational-bound.md`,
`findings/H91-witness-kraft-boost-budget.md`,
`findings/H92-kd-witness-kraft-sweep.md`,
`findings/H93-kd-paid-lotus-sweep.md`,
`findings/H94-normalized-rank-witness-sweep.md`,
`findings/H95-biased-expander-conservation.md`,
`findings/H96-neutral-transfer-operator.md`,
`findings/H97-sampled-neutral-transfer-sweep.md`,
`findings/H98-partial-slack-refresh-kernel.md`,
`findings/H99-seed-parity-readiness-ledger.md`,
`findings/H100-two-epoch-parity-exception-ledger.md`,
`findings/H101-neutral-parity-discount.md`,
`findings/H102-public-lane-local-class-grammar.md`,
`findings/H103-class-local-kraft-check.md`,
`findings/H104-spec-decode-scaling-audit.md`,
`findings/H105-forced-rewrite-collective-target.md`,
`findings/H106-cover-sequence-kraft-capacity.md`,
`findings/H107-value-shape-conservation.md`,
`findings/H108-prefix-record-grammar-converse.md`,
`findings/H109-nonprefix-referee-capacity.md`,
`findings/H110-partial-refresh-pareto.md`,
`findings/H111-collective-width-stream.md`,
`findings/H112-frozen-width-delta-law.md`,
`findings/H113-seed-class-partial-refresh.md`,
`findings/H114-frozen-delta-parity-refresh.md`,
`findings/H115-two-epoch-record-layer.md`,
`findings/H116-public-width-law-search.md`,
`findings/H117-parseable-width-symbol.md`,
`findings/H118-collective-width-amortization.md`,
`findings/H119-public-fixed-width-lanes.md`,
`findings/H120-width-channel-equivalence.md`,
`findings/H121-public-gap-typed-board.md`,
`findings/H122-public-gap-alphabet.md`,
`findings/H123-public-gap-table.md`,
`findings/H124-gap-table-fallback-repair.md`,
`findings/H125-public-raw-lane-repair.md`,
`findings/H126-raw-segment-boundary.md`,
`findings/H127-type-priced-refresh-sweep.md`,
`findings/H128-near-total-exception-threshold.md`,
`findings/H129-zone-prefix-raw-counts.md`,
`findings/H130-near-total-witness-margin.md`,
`findings/H131-typed-all-open-board-capacity.md`,
`findings/H132-self-consistent-width-selection.md`,
`findings/H133-common-cause-batch-witness.md`,
`findings/H134-modular-clock-readiness.md`,
`findings/H135-recurrent-transfer-operator.md`,
`findings/H136-batch-footprint-mask-dp.md`,
`findings/H137-bits-back-salt-flywheel.md`,
`findings/H138-bounded-reset-ratchet.md`,
`findings/H139-reset-ratchet-converse.md`,
`findings/H140-slack-refresh-supply-bound.md`,
`findings/H141-kraft-boundary-converse.md`,
`findings/H142-intrinsic-boundary-optimizer.md`,
`findings/H143-near-total-public-board-bound.md`,
`findings/H144-non-greedy-lookahead-value.md`,
`findings/H145-unfold-depth-stop-ledger.md`,
`findings/H146-slack-superposition-transfer.md`,
`findings/H147-upward-detour-collapse.md`,
`findings/H148-two-pass-selected-stream.md`,
`findings/H149-decode-composition-capacity.md`,
`findings/H150-selected-stream-dp.md`,
`findings/H151-closure-kraft-ledger.md`,
`findings/H152-superposition-gap-ledger.md`,
`findings/H153-cloud-q-conservation.md`,
`findings/H154-fixed-cell-closure-phase.md`,
`findings/H155-closed-lane-nongreedy-target.md`,
`findings/H156-completion-seed-mass-tradeoff.md`,
`findings/H157-recursive-selected-stream-dp.md`,
`findings/H158-opening-referee-scaling.md`,
`findings/H159-seed-bearing-closed-core.md`,
`findings/H160-seed-closure-transfer-matrix.md`,
`findings/H161-item-level-closure-economics.md`,
`findings/H162-item-stream-cover-dp.md`).
Singles wall:
`A/C/D/G-*.py`. PCTB position-tax dead end: `../proof_kernel/pctb_ledger.py`.
