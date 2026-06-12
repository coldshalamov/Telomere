# TELOMERE — SPECIFICATION (V1)

**This is the only specification.** Everything else in this repository is
analysis, history, or evidence. If any other document disagrees with this
one, this one wins. Read §0 and §1 before touching anything.

---

## 0. What Telomere is — and is not

Telomere is **generative seed-search compression**. Chance is the only
engine. A span of the stream is replaced by a short record naming a seed
whose hash expansion exactly reproduces that span; everything else rides
under literal markers. The stream is shuffled by one fixed public rule
and searched again. Decoding is **stateless**: the decoder derives
everything from the compressed bits and a tiny fixed header.

Telomere is NOT:
- pattern or structure compression (it never models content; the lottery's
  odds are identical for text, noise, or ciphertext),
- dictionary or entropy coding,
- a universal compressor (incompressible inputs ride as literals — the
  pigeonhole obligation is met by construction, cost ≈ raw + 3 bits).

**THE METADATA CONTRACT (the law of this project):** if the decoder can
derive a value, it is NEVER stored. No pass counts. No per-block hashes.
No birth tags. No length fields on literals. No per-record anything.
Violating this contract makes the design not-Telomere. The header is the
exhaustive list of stored values (§3). Every past failure of agents in
this repo began with sneaking in "just a little" metadata. Don't.

## 1. The machine (maintainer's architecture — normative)

- The file is split into **blocks of B bits** (Golden Config: B = 8).
- The working state is a **stream of items**. Initially every item is a
  literal-wrapped block. An item is always self-delimiting.
- **A pass** = search → replace → shuffle:
  1. SEARCH: hash seeds from 0 upward (depth schedule §5). Compare each
     expansion's prefix against the bits of every run of 1..A contiguous
     items (a block, or several blocks in a row). Collect the winning
     (seed, run) candidates.
  2. REPLACE: replace each winning run — **in place** — with a record
     `[arity codeword][Lotus seed]`, greedy largest-arity first, strict
     acceptance: record bits < replaced bits. A record then occupies ONE
     position in the stream, like any other item.
  3. SHUFFLE: permute the item stream with the fixed rule
     `i → (walk(5·i mod P) + 1) mod M` — multiply (P = least prime ≥
     item count M; outputs ≥ M re-walk), then shift by one
     (maintainer's fix: the bare multiply pins position 0 in place
     forever; the shift guarantees EVERY item moves EVERY pass).
     Exactly invertible: shift back, multiply back.
- Repeat until a pass replaces nothing (the empty probe does not
  shuffle). Emit: header + final item stream, with the trailing literal
  stretch as one REMAINDER RUN (§3).
- **Recursion**: the finished output file may be fed back in as a brand
  new input (re-blocked, fresh run). That is the only between-runs
  operation; nothing inside a run re-compresses an existing record
  except by bundling it into a larger record, which is normal replacement.
- **Dice freshness**: expansion keys are salted by POSITION — the item's
  position at match time. At decode the salt is SELF-PRESENTING: when
  the reverse walk arrives at a pass's state, that pass's records sit at
  exactly their match positions, so the salt is just the current
  position. Costs nothing. The +1 shuffle moves every item every pass
  and re-pairs neighbors, so positions and pairings both refresh — fresh
  lottery draws, zero stored state.

## 2. Record decode (maintainer's construction — verbatim semantics)

1. Decode the Lotus field to an integer seed; hash it (with its position
   salt). The digest is generated LONG — far longer than the record.
2. Read the digest's prefix as items: a literal marker means exactly B
   raw bits follow; a record marker means an arity header and a
   self-delimiting Lotus seed — recurse on it, in place.
3. Stop after reading {arity} items' worth of blocks. Bits dangling past
   that point are the encoder's truncation excess — extraneous by
   construction, discarded.

A block can be a literal, a match, or a bundle; until decoded it is
unknown; it is always one item and every item is treated the same.
Expansion is IN PLACE: a bundle's blocks come out contiguous, one after
another, exactly where the record sat. No length is ever stored because
none is ever needed: Lotus delimits itself, arity counts the reads, the
remainder-run length comes from the header.

## 3. Wire format

**Header (exhaustive — nothing else is ever stored):**
`TLMR`, version byte, then Lotus-coded: block size B, original_len,
last_block_size, alphabet-profile bit, checksum (truncated SHA-256 of
the original, ~64 bits, constant size). Every field is underivable. The
checksum is the referee for trial decoding (§4) and the integrity check;
it does not grow with the file.

**Alphabet (Kraft-complete, constant per file; profile bit selects):**

| codeword | canonical (default) | payback (option) |
| --- | --- | --- |
| 2-bit ×2 | arity-1 `00`, arity-2 `01` | literal `00`, arity-1 `01` |
| 3-bit ×4 | literal `111`, arities 3–5 | arities 2–5 |

Canonical is the Golden Config default: the 2-bit arity-2 doubles the
engine channel's hit rate (measured, exact).

**Seed field:** J3D1 Lotus — 3-bit jumpstarter, unfolding length field,
payload (cap 508 bits; costs pinned in `cost_pin_report.json`). Smallest
record: 7 bits.

**Literals:** `[marker][B raw bits]`, no length field. One REMAINDER RUN
allowed: a single marker whose payload runs to end of stream, length
derived from the header. Untouched-file worst case: raw + 3 bits + header.

## 4. Decoding (stateless — the maintainer's rule)

Inputs: compressed bits + header. The decoder performs **the exact same
actions as the encoder, in the exact same order, in reverse**: undo a
shuffle, open that pass's records in place (each at its
then-current position, which IS its salt — self-presenting, free),
repeat; strip literal wrappers when the stream length matches the
header. Everything is derived, nothing stored:

- **How many reverse steps**: derived — keep reversing until the stream
  is all literals and the length matches the header (records only vanish
  by being opened; every real pass left at least one).
- **Which records open at each reverse step**: derived by the
  maintainer's rule — **keep what decodes** ("multiple decodings"):
  try the openings; wrong openings either contradict the stream's
  structure or fail the header checksum; the reading that checks out is
  the answer. **Demonstrated in this exact architecture:**
  `model_analysis/proof_kernel/robins_opening_rules.py` — keep-what-
  decodes 12/12; the two fixed mechanical rules (open-everything-each-
  step, carry-all-to-the-end) 0/12 each. Trial decoding is the design,
  not a fallback. Supplementary evidence: `v1_roundtrip_proof.py`
  (36/36 in an equivalent analysis model). The open quantitative
  question — decode search cost and surviving-reading count as files
  grow — is tracked in `docs/GOLDEN_CONFIG.md` §5 and §7, with charged
  1-bit escapes specified as the fallback if scale demands it.

## 5. Search schedule

Depth is a compute knob, never a compression knob: seeds whose records
cannot beat any live run of blocks are provably worthless (depth ceiling
D*). The Golden Config searches the compressive frontier only — e.g. at
B=8, arity 2, canonical: the 253 seeds whose records beat 16 bits.

## 6. The Golden Config (see docs/GOLDEN_CONFIG.md for the full study)

| parameter | value |
| --- | --- |
| block size | 8 bits |
| alphabet | canonical |
| engine arity | 2 (arities 3–5 optional) |
| seed field | J3D1 Lotus |
| depth | compressive frontier only |
| passes | 16–64 per run |
| recursion | re-run on output |

What "working" means, precisely: decode always works; files whose
reachable-span density clears the threshold compress; everything else is
bounded at raw + ε. On purely random data the density sits below
threshold at every parameter setting — that is a counting law, not a
tuning failure — and the program's research lane is the density
mechanism (`docs/GOLDEN_CONFIG.md` §7).

## 7. Where the real code goes

`IMPLEMENTATION_MAP.md` at repo root lists the module slots (header,
Lotus, expander, search, shuffle, encoder loop, trial decoder). The
legacy Rust in `src/` implements an OLD wire format — useful as
scaffolding reference only; do not extend it as-is.

## 8. Evidence index (claims → artifacts)

- Stateless decode in THIS architecture, maintainer's keep-what-decodes
  rule: `robins_opening_rules.py` 12/12 (fixed opening rules 0/12).
- Stateless multi-pass decode, zero metadata (analysis model):
  `v1_roundtrip_proof.py` 36/36.
- Shuffle bijectivity + zero repeated neighbors: `shuffle_rules_eval.py`.
- Exact format arithmetic (gaps, win sizes, seed counts): `golden_format_arithmetic.py`.
- Coverage dynamics, real draws: `golden_mc.py`, `monte_carlo_v1.py`.
- Break-even thresholds: `golden_break_even.py`.
- Lotus cost pins: `cost_pin.py` / `cost_pin_report.json`.
- Falsified dead ends (do not revisit): `docs/GOLDEN_CONFIG.md` §6,
  `docs/TELOMERE_RESULT_LEDGER.md` (history with evidence classes).
