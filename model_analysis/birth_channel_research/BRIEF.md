# Birth-Channel Research — shared brief (read this fully before any work)

**Mission.** Find a *verifiable working configuration* for Telomere's
multi-pass loop in which ALL of the following hold simultaneously, or prove
precisely which one cannot. This is a real, repo-acknowledged open problem
(MATH_MODEL_V1 §8 / GOLDEN_CONFIG §7 / THE_OPEN_QUESTION / Result-Ledger
Correction Notice 3).

**Read this first — the master gate.** A birth channel that is *free* AND
*content-blind* AND *unbounded* (works for arbitrarily many passes) **is a
pigeonhole violation.** They are the same wall from two sides: by
content-blindness, anything that works on structured data works on random data
too; a free unbounded channel would then convey the births — which are uniform
hash outcomes, hence incompressible (Shannon) — for free, mapping 2^n random
inputs into fewer outputs. Impossible. Therefore:

> **Every `working-config` claim must FIRST pass the counting gate:** "If this
> mechanism were free and content-blind, would arbitrary random data
> net-compress without bound? If yes — STOP, you have a leak; find the
> currency it actually pays in (below). If genuinely no, explain what *finite*
> resource bounds it."

The counting law is not avenue H running in parallel. It is the gate every
candidate walks through. The realistic, valuable prizes are therefore:
**(a) a sharp impossibility** (the conservation theorem, with the one
assumption it hinges on), and **(b) the quantified max-free-reach K** — the
largest pass count over which near-free compounding is achievable, with the
optimal config and the next bottleneck named. **Prize (b) is the central
constructive goal** — it is the honest answer to "sustain the match rate
without a massive end-metadata tax," just with a finite K rather than ∞. A
true unbounded free channel is a possible-but-extraordinary outcome that must
survive the gate above; do not report it without surviving it.

The four pieces that must come together:

1. **Sustained match rate via salting.** Each pass re-salts the hash so the
   lottery refreshes; a block can match on pass *t* though it missed earlier.
   Per-(block,pass) match probability stays ≈ 2^−gap and does not exhaust.
2. **Stateless decode.** The decoder reverses every pass from the final state
   + a tiny fixed header. Crucially it must learn, for each record, **which
   pass it was born on** (so it opens/unbundles at the right reverse step and
   salts with the right key) — with **no per-record stored metadata**.
3. **Bounded arrangement cost.** Positions are **derived from the public
   shuffle rule, not stored.** A *fixed-size* board (modular wrap) so that as
   blocks bundle, the survivor set shrinks and the arrangement bill shrinks
   with it — never grows. (This is the maintainer's fix to PCTB; see below.)
4. **Net ≥ 2 bits per match.** After charging (2)+(3) and Lotus/arity headers,
   each match nets > 0. ~2 bits/match is the target.

If all four hold, recursive (re-run on output) compounding is unlocked.

---

## ⚠ "Settled" means settled BELOW THE WALL only (≤ ~6 passes)

The decode proofs below all live in the *free-channel regime*:
`v1_roundtrip_proof.py` is **T ∈ {2..5} passes**; the explosion check covers
**~6 passes**. They prove the mechanics are sound *where birth is already
cheap*. **They say nothing about the regime where the wall actually is.** The
hard problem is **sustained arity-1 singles across tens-to-hundreds of passes
with fresh salts every pass.** A toy that round-trips at 5 passes is necessary
but proves *nothing* about the wall — do NOT cite ≤5-pass round trips as
evidence a channel scales. Treat the affine-stride bundle-epoch "solution" as a
*lead to stress-test at high pass count*, not a foundation: the ledger's own
Correction Notice 2 records a previous decode "proof" that "dodged the hard
case" by paying carriage no kernel charged. **Test at high T or it doesn't
count.**

## What is ALREADY SETTLED — do NOT relitigate (cite the artifact instead)

- **Decode mechanics, multi-pass, zero metadata, at toy scale:** PROVEN.
  `proof_kernel/v1_roundtrip_proof.py` 36/36; `robins_opening_rules.py` 12/12
  (keep-what-decodes beats fixed rules 0/12). In-place expansion, remainder
  run, derived pass count, literal skip-termination: proven.
- **Shuffle reversibility** (`i→walk(5i mod P)+1 mod M`, exact inverse; zero
  repeated neighbor pairs): `shuffle_rules_eval.py`.
- **Position salts are self-presenting** at the *correct* reverse pass (the
  record sits at its birth position once the later shuffles are undone).
- **Bundle (arity ≥ 2) birth epoch** is claimed solved by the **affine-stride
  fingerprint** (Result-Ledger CN2/CN3, `v1_roundtrip_proof.py`). Treat this
  as a *lead to extend*, and also a *claim to stress-test*, not gospel.
- **E[win | hit] ≈ 2 bits** at every scale (exact counting, MATH_MODEL §2).
  Viability is a hit-DENSITY question, never a hit-SIZE question.
- **The free partial birth channel — the explosion check (~2.5 bits/record).**
  A wrong-salt expansion does NOT terminate cleanly: it fails to parse as
  self-delimiting items / leaves dangling garbage / fails the checksum. So at
  decode you can TRIAL a record's birth pass and detect the right one by
  *non-explosion*. Measured budget ≈ 2.5 bits/record ≈ distinguishes ~5–6
  candidate passes for free (Result-Ledger row 7 / PLAIN_STATUS). **This is
  the only free source found and it is load-bearing — every avenue should ask
  how to combine it with structure to extend past ~tens of passes.**

## The PCTB lesson (a dead end already measured — do not repeat)

`proof_kernel/pctb_ledger.py`. Storing **explicit final positions** on an
**expanding** board costs log2 C(Q_P, N_P) ≈ N·(log2 Q_0 + P·log2(branching))
bits — it **breaks the raw+ε bound**, bloating 22× at 64 passes on
incompressible data, because the board MUST grow (to keep the size schedule
decoder-derivable) so even carries pay a per-pass address tax. **Rule that
falls out: never store positions; never let the board grow per pass.**
Positions must be *derivable* from the public shuffle, or *implicit* in
enumeration order, on a *fixed* board.

---

## THE WALL — state it exactly

Everything reduces to **one channel**:

> A **content-blind, deterministic, sub-2-bit (ideally zero-bit)** channel that
> conveys each record's **birth pass** at decode — in particular for
> **arity-1 (singles)**, the unbounded grinding channel that drives
> compounding. Bundles may already have this (affine-stride); singles do not.

Why singles are the crux (Result-Ledger CN2/CN3): arity-1 replacements are
length-preserving (1→1), so the permutation-unwind needs only *bundle* birth
epochs — which the affine-stride fingerprint supplies. But the *salt refresh*
that sustains the match rate needs *every* record's birth pass, singles
included; and singles have no stride (one slot, no span) to fingerprint.

The standing impossibility argument to BEAT or SHARPEN (THE_OPEN_QUESTION):
*"the births are the dice outcomes; a uniform hash makes them independent and
uniform, hence incompressible; the 'which pass' half is the unpayable
remainder."* The maintainer has overturned one impossibility in this project
before (the 2-bits/block total cap). So: attack it, don't worship it — but if
you cannot break it, **localize exactly where and in which currency the bill
reappears.**

## Conservation principle — name the currency

Every mechanism ever tried pays the birth bill in one of these currencies.
For ANY candidate you propose or test, you MUST state which currency it spends:
`stored bits` · `hit density` · `match supply` · `wrap/carriage` ·
`structure (free ~2.5 bits)` · `compute that scales with 2^bits`.
A candidate that claims "free" in all currencies is almost certainly wrong —
find the leak before reporting success.

---

## PROTOCOL — mandatory for every agent (the maintainer's rules)

1. **Hypothesis before test.** Never run a script without first writing: *what
   do I expect this to show, and why?* Predict the outcome from the mechanics.
2. **Would the test even work?** Before any hashing test, compute the expected
   match rate. Matches occur ≈ once per 2^gap attempts (gap ≈ 8–13 bits at
   B=8). Hashing 256 times and finding nothing is EXPECTED and proves nothing.
   If your test needs a match to occur, ensure the parameters make one *likely*
   (e.g. plant a known seed→span, or shrink B so 2^B is small), or make the
   test about *counting/logic*, not luck.
3. **Prefer math, logic, unit tests, exact counting.** Real "does it compress"
   runs on this laptop will NOT show net compression (density ≪ threshold);
   do not use them as evidence for or against. Use them only to verify
   *mechanics* (reversibility, determinism) at toy scale.
4. **Distinguish what you proved from what you assumed.** Every claim carries
   an evidence class: `proven-by-construction` (runnable, end-to-end) ·
   `proven-by-math` (derivation) · `measured` (real draws, toy) · `conjecture`.
5. **Do not invent stored metadata** to make decode work. SPEC §0: if the
   decoder can derive it, it is never stored. A solution that stores the birth
   pass is not a solution (it's the priced `tags` baseline: ≥ log2(passes)
   bits, already net-negative past pass ~6).
6. **Persist.** If an avenue stalls, do not stop — try the next sub-idea, or a
   weaker version, or a sharper impossibility. Report partial structure.

---

## CANDIDATE AVENUES (seed ideas — extend, combine, or refute)

A. **Modular-orbit / affine-stride epochs for SINGLES.** The affine-stride
   fingerprint gives bundle epochs. Can a prime-field shuffle (i→g·i mod p, g
   a generator; or affine i→a·i+b) make a *single's* birth pass readable from
   its orbit phase? A single has no span — but it has a trajectory. Does the
   orbit position constrain candidate birth passes to a small set the
   explosion check can then disambiguate?

B. **Trial-decode ambiguity is actually bounded ⇒ no channel needed.** Maybe
   "keep-what-decodes" + the explosion check already pins birth pass with
   bounded surviving readings. Prove or refute a bound on the number of
   self-consistent decodings as a function of (N, P). If it's polynomial /
   constant-per-record, deterministic decode is real (Result-Ledger Q1).

C. **CRT / residue clocks on a fixed board.** Board size Q = ∏ p_i. A slot ↔
   residue vector. A pass advances a "clock" coordinate. Can a bounded odometer
   in the residue structure carry a per-record birth-pass register that is read
   from position (derived, not stored)? Watch the capacity: a fixed board holds
   only log2(Q) bits total — check it against the N·log2(P) needed.

D. **Fibonacci / Zeckendorf / Lucas bounded registers.** Number-theoretic
   addressings where "how many times shuffled" leaves an additive signature.
   Zeckendorf representations are unique and shift-structured — does a
   Fibonacci-stride shuffle make pass-count readable mod something?

E. **Explosion-check amplification.** The free ~2.5 bits/record disambiguates
   ~6 passes. Combine with ANY structure that narrows candidate births to ≤6:
   e.g. an alphabet/salt schedule with period 6, or an orbit that only revisits
   a slot every 6 passes. Then 2.5 free bits cover the residue and the schedule
   covers the quotient. Quantify the reach. **LEAK WARNING (the trap here):** a
   period-P salt schedule that lets the explosion check disambiguate also
   *reuses the same lottery every P passes* → the dice stop refreshing → the
   bill reappears in the `match-supply` currency (geometric starvation,
   Result-Ledger row 9 / PLAIN_STATUS row 9, measured ~2× supply loss per bit
   gained). Any schedule-based narrowing MUST account for this; report the net
   after the supply loss, not the gross reach.

F. **Frozen-record / two-speed boards.** Once a record is born it stops moving
   (or moves on a slower clock) while literals shuffle fast. Does freezing make
   birth position (hence salt) self-presenting AND birth pass readable from the
   gap between fast and slow clocks? Check reversibility carefully.

G. **Parity / sign channels (cheap, ≤1 bit).** A ≤1-bit-per-record derivable
   signal (e.g. slot parity under an involution) that, combined with the
   explosion check, extends reach by one more bit. Cheap but compounding.

H. **Sharp impossibility (the skeptic's constructive output).** If birth pass
   is genuinely incompressible, produce the cleanest possible theorem: define
   the channel formally, show the births' entropy lower-bounds any decodable
   representation, and identify the *single* assumption that, if relaxed (e.g.
   non-uniform hash, content-coupling, partial determinism), would break it.
   A precise impossibility is a valid, valuable deliverable.

---

## SUCCESS / FAILURE CRITERIA

- **MAX-FREE-REACH K (the central constructive prize):** the largest pass
  count K over which near-free compounding holds, with the optimal config
  (board/shuffle/salt/alphabet/arity/channel), an *exact ledger* (counting,
  not a laptop compression run) of net-per-match after charging the channel,
  the currency budget, and the **named next bottleneck** at K+1. This is the
  honest answer to the user's actual goal. Quantify K; do not hand-wave it.
- **SHARP IMPOSSIBILITY:** a clean proof that one of the four pieces cannot
  hold content-blind *unbounded*, with the exact assumption it hinges on
  (this is what the counting gate produces when a candidate fails it cleanly).
- **WORKING CONFIG, UNBOUNDED (extraordinary — must survive the master gate):**
  same as max-free-reach but with K = ∞. Before reporting this, you MUST
  answer the counting gate in writing and exhibit why random data does NOT
  net-compress under it. An unbounded free content-blind channel is a
  pigeonhole violation; if you cannot explain why yours isn't, it isn't —
  it has a leak and your job is to find it, not to report the false positive.

Anything else (vague "this might work", an untested mechanism, a test with no
hypothesis, a claimed match from luck) is **not** a deliverable — keep going.

## OUTPUT FORMAT (every agent returns)

```
AVENUE: <letter/name>
HYPOTHESIS: <what you expected and why, before testing>
MECHANISM: <precise construction: board/shuffle/salt/birth-channel>
RESULT: working-config | sharp-impossibility | partial(reach=K) | refuted | stalled
EVIDENCE: <class> — <artifact path or derivation>; would-the-test-work check
CURRENCY: <which conservation currency the birth bill is paid in, and how many bits>
NEXT: <the single most promising next sub-idea if not done>
```

Findings go in `model_analysis/birth_channel_research/findings/<avenue>.md`.
Runnable toys go in `model_analysis/birth_channel_research/` (toy scale,
real SHA only where a hypothesis says a match is plausible; else pure math).
