# Lane P2 — Explosion-budget (re-measuring the single point of failure)

Researcher pass, June 2026. Exact-counting from the REAL J3D1 Lotus grammar.
Toy: `model_analysis/birth_channel_research/P2-explosion-budget_exact.py`
(pure combinatorics, NO luck-hashing). Anchored to the repo's measured ~2.5.

**Headline.** The free explosion budget `E` is **not a flat per-record
constant**, and it is **exactly zero on the arity-1 singles channel** — the
unbounded grinder the whole WALL is about. This is forced by two exact facts,
salt-scheme-independent: (i) the item alphabet is a **complete prefix code**
(Kraft sum `= 2·2⁻² + 4·2⁻³ = 1.0`) and the Lotus length-field bijects onto the
valid payload widths (tier_width `tw` ⇒ exactly `2^tw` widths = a `tw`-bit
field's capacity), so a uniform digest parses into a clean self-delimiting item
stream with probability `-> 1` (`E_parse = 0`); (ii) arity-1 means **exactly one
item by definition**, and one item is length-unconstrained in *both* candidate
state models (block-model: any `B` raw bits is a valid block; item-model:
completeness), so there is no length to violate. Hence **`E(a=1) = 0`**: the
free explosion budget never reaches singles. Length-pinned cases (known target
span `L`, e.g. bundles) do carry a finite budget — `E_len` ranges ~2.7–7.6 bits
over `(a, L)`, in the magnitude ballpark of the repo's folklore ~2.5 (exact
repo derivation not located; no reproduction claim made). Raising `E` is **not
free**: it costs stored self-check bits paid against the per-record win (~1–2
bits), so `E_max` is finite and small. **No achievable `E` makes `c_mean(T)=0`
for any `T>=2`.** The sharp converse form: sustaining `T` passes needs `E` to
GROW as `log2(T)-O(1)`; a constant free budget shifts the birth bill's
intercept, never its slope. Net bill stays `N*(log2(T)-E) -> infinity`.

---

## HYPOTHESIS (written before testing, from the mechanics)

A wrong-salt expansion "does not explode" iff it parses as exactly `arity`
self-delimiting Lotus items with consistent lengths. The bits of constraint =
`E = -log2(q)`, `q` = false-non-explosion rate. I expected: (a) `E` is bounded
by the record's own bit budget (a longer self-check is literal bits that do not
compress), so raising `E` trades against the win; (b) even maximal `E` leaves
`c_mean(T)=log2(1+(T-1)2^-E)>0` for all `T>=2`, so the impossibility stands.

**Both held, but the mechanics forced a sharper result than predicted:** the
constraint that actually bites is the *length* pin, not the parse, and the
length pin is absent on the singles channel.

---

## MECHANISM (precise construction)

Grammar (SPEC_V1 §3, `costs.py` mirror), B=8, canonical alphabet, J3D1 Lotus:
- LITERAL item = `[111][8 raw]` = 11 bits, self-delimiting (fixed B).
- RECORD item = `[arity codeword][J3D1 Lotus seed]`; Lotus seed =
  `[3b jumpstarter = tier_width-1][tier_width-bit length field][payload]`,
  self-check `lotus_width(payload_width) == tier_width`.

`q` is computed exactly two ways:
- **`E_parse`** = parse as exactly `a` items, *no* length pin (the weakest check).
- **`E_len(a,L)`** = parse as exactly `a` items AND total wire length `== L`
  (the full check; requires a KNOWN target span length `L`).

`E_len` via exact DP: `avalid(a,L)` = number of `L`-bit strings parsing as
exactly `a` valid self-delimiting items; `n_item_strings_of_len(w)` counts
distinct valid item strings of length `w` (literal: `2^B`; record: for each
consistent `(arity, tier_width, payload_width)`, the jumpstarter+length-field
are fixed and the payload is free, `2^payload_width`). Then
`E_len(a,L) = L - log2(avalid(a,L))`.

---

## RESULTS (exact)

### (1) Parse-only supplies NO budget — the grammar is Kraft-complete

`p1` (prob a uniform prefix STARTS with a valid item), counting item lengths
up to window `W`:

| W | 16 | 32 | 64 | 96 | 128 | 200 | 300 | 500 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p1 | .324 | .464 | .592 | .657 | .712 | .780 | .850 | .936 |
| E_parse = -log2 p1 | 1.63 | 1.11 | 0.76 | 0.61 | 0.49 | 0.36 | 0.23 | 0.10 |

`p1 -> 1` monotonically; `E_parse -> 0`. **Proven-by-math, not just measured:**
the alphabet is a complete prefix code (Kraft `= 2·2⁻²+4·2⁻³ = 1.0`) and the
Lotus length-field bijects onto valid payload widths — for tier_width `tw`,
exactly `2^tw` payload widths satisfy `lotus_width(pw)==tw`, the full capacity
of a `tw`-bit field (verified `tw=1..8`). The only defect is the single unused
`tw=1` codepoint (1 of 2 used), which is why `p1` converges to *just below* 1
per finite item; across long items it `-> 1`. So a wrong-salt digest almost
always parses; **parse-only supplies no budget.** (The implemented decoders'
record-opens never explode either — but those are fixed-width `SEED_BITS=14`
toys that *cannot* explode for any arity by construction, so they corroborate
rather than prove; the proof is the completeness math above.)

### (2) Length-pinned cases DO carry a finite budget (requires a known L)

| a | L (span) | E_len | q |
| --- | --- | --- | --- |
| 1 | 11 (1 literal block) | 2.715 | 0.152 |
| 2 | 22 (2 literal blocks) | 5.249 | 0.026 |

`E_len` ranges ~2.7–7.6 bits over the swept `(a, L)` (the `L=11` entry is a
local spike because it is the one-literal-item span). This is the *same
magnitude* as the repo's folklore "~2.5 free bits/record" (PLAIN_STATUS row 7:
"true expansions terminate; wrong-salt ones explode" — a termination/length
pin, exactly this family). **I could not locate the repo's exact derivation of
2.5, so I make no reproduction claim** — only that length-pinned budgets are in
this range and are the family the folklore number belongs to. Crucially this
budget exists **only when the decoder independently knows the span length `L`**
(bundles via affine-stride placement; literal spans whose length is fixed).

### (3) For the singles channel, L is NOT known => E(a=1) = 0 (proven-by-math)

`E(a=1) = 0` follows from two exact facts, **independent of the salt scheme and
of which state model is used**:
- Arity-1 means the decoder reads **exactly one item** from the expansion
  (SPEC §2.3: read `arity` items, discard the rest).
- One item is length-unconstrained in *both* state models: in the
  constant-N **block-model** the single is exactly `B` raw bits, any value of
  which is a valid block; in the **item-model** the grammar is complete (§1),
  so any prefix is a valid self-delimiting item. Either way there is **no
  length and no parse the wrong salt can violate**.

So `q = 1`, `E(a=1) = 0`. A single is length-preserving (1 item -> 1 item) — the
length-preservation lemma (Result-Ledger CN2) is exactly why there is nothing
to pin against. **The free explosion budget never reaches the singles
channel** — the exact channel THE_OPEN_QUESTION names as the unbounded crux.
The repo's "~2.5 free bits/record", stated per-record, **silently over-credits
singles** (it is an arity≥2 / known-`L` phenomenon). The implemented decoders'
arity-1 paths (`v1_roundtrip_proof.py` L165-170 generates exactly `B` bits with
no check; `robins_exact_spec.py` L83-84 reads one item, never rejects) are
consistent with this, but the proof is the two facts above, not those
non-exploding toys.

### (4) Joint ceiling N*(T) (round-2 formula, grammar E)

`c_mean(T) = log2(1+(T-1)q)`, `N*(T) = 64 / c_mean(T)`:

| reading | q | N*(64) | N*(256) | N*(1024) |
| --- | --- | --- | --- | --- |
| singles, decode-faithful `E=0` | 1.000 | 10.7 | 8.0 | 6.4 |
| singles, generous pin `E=2.71` | 0.152 | 18.8 | 12.0 | 8.8 |
| bundle a2, pinned `E=5.25` | 0.026 | 45.4 | 21.7 | 13.3 |

At the decode-faithful singles value `E=0`: `c_mean(T)=log2(T)` exactly — the
**full tags bill, zero free discount**, on the unbounded grinding channel.

### (5) Cost to raise E is STORED-BITS, capped by the per-record win

To raise `E` by `b` bits you add `b` bits of format redundancy / self-check
(lower `q` by `2^-b`). Those are literal, incompressible record bits — they
cost the win directly. Per-record win `E[win|hit] ~= 2` bits (a2), `~= 1` bit
(single). So `E` rises at most ~1–2 bits above native before record bits >
replaced bits and strict acceptance (record < replaced) kills the match.
`E_max(singles) ~= 1`, `E_max(a2) ~= native+2` — finite, small. This is a
**tighter cap than the record-length bound**. Even at `E_max`,
`c_mean(T) > 0` for all `T>=2`.

### (6) Converse-form impossibility (the conservation theorem)

For large T, `c_mean(T) -> log2(T) - E`. Holding the residual bounded as T
grows requires `E` to GROW as `log2(T)-O(1)`. A *constant* free budget (native
2.5 or raised) is a constant discount on a bill that still scales `N*log2(T)`:

| T | log2 T | residual log2(T)-E_max, E_max in {0, 1, 2.71, 5.25} |
| --- | --- | --- |
| 6 | 2.58 | 2.58 / 1.58 / 0 / 0 |
| 64 | 6.00 | 6.00 / 5.00 / 3.29 / 0.75 |
| 1024 | 10.00 | 10.00 / 9.00 / 7.29 / 4.75 |
| 1e6 | 19.93 | 19.93 / 18.93 / 17.22 / 14.68 |

Every column grows without bound in T. **The free budget shifts the
intercept, never the slope.** Net birth bill `= N*(log2(T)-E) -> infinity`.

---

## WIDEST ACHIEVABLE FREE (N,T) REGION AND THE K IT IMPLIES

- The widest *pinned* `E` available at B=8/J3D1 is the bundle case
  (`E_len(a=2,L=22)=5.25`), giving the largest finite joint region
  `N*(T)=64/log2(1+(T-1)*0.026)` (e.g. N*=45 at T=64, N*=13 at T=1024).
  This is the bundle channel — which already has the affine-stride epoch
  fingerprint and is NOT the open problem.
- For the **singles channel that drives compounding**, the decode-faithful
  budget is `E(a=1) ~= 0`, so the free reach is `N*(T)=64/log2(T)`: ~11
  records free at T=64, ~6 at T=1024 — a tiny *joint* region, NOT a flat K.
- **No achievable `E` makes `c_mean(T)=0` for any `T>=2`.** `E_max` is finite
  (capped by the ~1-2 bit win), so the impossibility is unconditional.

So the honest **K** is not a free pass count: it is a finite joint `(N,T)`
ceiling `N*(T)=64/c_mean(T)`, collapsing to `T=1` as `N -> inf`. The next
bottleneck at `K+1` is **stored-bits** (`c_mean(T)` per record = the tags
baseline minus the constant `E`).

---

## COUNTING GATE (answered in writing)

**Q: explosion check free + content-blind + unbounded => random data
net-compresses without bound?** That is a pigeonhole violation. **A: it is
NOT free-and-unbounded on the channel that matters.** Parse-only is free but
supplies `E~=0` (Kraft-complete grammar, `p1->1`). The length pin supplies the
real ~2.5 bits but is FINITE and content-blind (a wrong-salt digest survives at
fixed rate `q=2^-E`, a filter not an oracle), and it **does not fire on
singles** (no known target length). Raising `E` is stored-bits capped by the
win. The residual `log2(T)-E` is uncovered by anything free and grows without
bound in T. **No free, content-blind, unbounded channel exists** — the bill
reappears in `stored-bits`.

---

## CURRENCY

| mechanism | currency | bits |
| --- | --- | --- |
| parse-only "explosion" | `structure-free` but `E~=0` | grammar Kraft-complete; no budget |
| length-pinned explosion (bundles / known-L spans) | `structure-free`, FINITE | `E_len`, e.g. 2.71 (a1,L=11), 5.25 (a2,L=22); never reaches singles |
| raising E | `stored-bits` | +b self-check bits, capped by the ~1-2 bit win => E_max small/finite |
| **residual past the joint ceiling** | **`stored-bits`** | `c_mean(T)=log2(1+(T-1)2^-E) -> log2(T)-E`; unbounded in T |

**Primary currency: `stored-bits`.** The free length-pinned budget is a
constant discount; the unavoidable residual `log2(T)-E_max` is paid in tags.

---

## EVIDENCE CLASSES

- Grammar is a complete prefix code (Kraft `=1.0`) + Lotus length-field
  bijection (`2^tw` widths per tier_width): **proven-by-math** (exact, verified
  `tw=1..8`). ⇒ `p1 -> 1`, parse-only gives `E_parse = 0`.
- `E(a=1) = 0` on the singles channel: **proven-by-math** (arity-1 = one item
  by definition + one item length-unconstrained in both state models; the
  non-exploding toys merely corroborate — they cannot explode by construction,
  so they are not the proof).
- `E_len(a,L)` exact table (length-pinned budgets ~2.7–7.6): **proven-by-math**
  (exact DP). Magnitude consistency with folklore ~2.5 noted; **no reproduction
  claim** (repo's exact derivation not located).
- Raising E costs stored-bits capped by the win; E_max finite:
  **proven-by-math** (strict acceptance: record < replaced).
- Converse impossibility `residual -> log2(T)-E`, net bill `N*(log2(T)-E)`:
  **proven-by-math** (round-2 `c_mean` asymptotics + this lane's E).
- The `q = 2^-E` identification is **conjecture** in its exact constant
  (per-trial independence is an idealization; the `E_len` arithmetic is exact).

## NEXT (single most promising sub-idea)

The one residual lever this lane did not fully close: whether the *single's*
home-slot decode can be given a length pin for FREE by coupling it to a
block-aligned structural invariant (constant-N block-state forces whole-B-bit
bottoming-out). If a single's expansion could be forced to fail unless it
bottoms out in exactly the B-bit blocks the slot demands, `E(a=1)` would jump
from ~0 to the `E_len(a=1,L=B-span)` value — but that pin must be DERIVABLE,
not stored, and the length-preservation lemma (1->1) suggests there is nothing
to pin against. Pin this precisely: does constant-N block-state already supply
a derivable per-single length, or is the single genuinely length-free?
