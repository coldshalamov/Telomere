# Telomere — The One Open Question (written down so no session forgets)

*June 2026. This file exists because the maintainer and the agent kept
re-walking the same ground. Read this before discussing decoding. Plain
words only: block, seed-block, literal, pass, walk, shuffle, salt.*

## The maintainer's decode procedure (his words, condensed)

Encode: each pass = search seed space, replace matches in place (salt =
the block's position at that moment), then shuffle (x5, +1). Repeat.
Decode: unshuffle once (-1, divide by 5); walk the string; decode every
seed-block at its CURRENT position as salt; skip literals; unshuffle
again; repeat. When a walk finds only literals: unwrap them per the
file header. Nothing stored: no pass counts, no per-block metadata.

## The arithmetic at the center of the dispute

A seed-block made in pass 1 at position 4 (salt 4) has TWO shuffles
applied after its creation (pass 1's and pass 2's). The decoder's first
walk undoes ONE of them. So on walk 1 that seed-block stands at the
position pass 2 saw it — one unshuffle short of position 4.

- Decode it where it stands and the hash runs with the wrong position:
  different bits come out than it was created to stand for. The file
  decodes "successfully" into the wrong bytes.
- Leave it encoded for one more walk and it returns to position 4,
  where the current-position rule gives back its true bytes.

## What has been run (real SHA-256, the procedure implemented verbatim:
`model_analysis/proof_kernel/robins_exact_spec.py`)

Files built with 2 passes, containing at least one pass-1 seed-block
that survived pass 2 unmatched:

| decode rule | exact round trips |
| --- | --- |
| decode every seed-block on every walk (the procedure as stated) | 0/9 |
| pass-1 survivors stay encoded until walk 2 (everything else identical) | **9/9** |

Trace evidence from trial 1: encode log shows `pass 1: position 4
matched seed 6523 (salt 4)`; the walk-1 decode log shows the same seed
6523 being opened `at position 0 with salt 0`. Same seed, wrong
position, wrong bytes.

## The open question, exactly

On walk 1, a pass-2 seed-block (home, ready) and a pass-1 survivor
(one unshuffle from home) are byte-for-byte the same kind of object.
**What rule, costing no stored bits, tells the walk which seed-blocks
are not home yet?** Answer that and the 9/9 column is the whole
machine, fresh dice and all. Until then the proven configurations are:
salted machine with the survivors-wait rule supplied from outside the
wire (works, but the wire doesn't supply it), and the unsalted machine
(decodes by pure rule-following, dice never refresh — match supply
exhausts; maintainer has ruled this out as the configuration).

## Status of everything else (so it isn't relitigated)

Settled and proven: shuffle reversibility (x5+1, exact inverse), Lotus
self-delimiting decode, arity reads, dangling-bit chopping, in-place
expansion, remainder run, derived pass count, literal skip-and-unwrap
termination, the metadata contract. None of these are in question.

## Adjacent fields surveyed (June 2026 — so the search isn't repeated)

The missing quantity is per-record birth information (~log2(passes) bits)
through a write-once channel. Known tricks from the literature, checked:

- **Bits-back coding**: lets recoverable choices carry payload for free.
  Requires recoverability first — exactly what's missing. NOTE: if any
  partial birth-inference is ever found, bits-back converts it directly
  into reclaimed payload. The multiplier exists; the key doesn't.
- **ANS / arithmetic coding**: efficient channels; information still
  paid at full entropy. No discount.
- **Sequence CRDTs** (stable addresses under insertion): confirms the
  address result — identity inferable for free, history not.
- **Reversible computing (Bennett)**: needs the forward input (the
  original file). Circular for decoding.
- **Trellis/convolutional codes**: timing from structure, paid in
  deliberate redundancy (= tags by another name).

**Closure**: the births ARE the dice outcomes. A good (uniform) hash
makes them independent and uniform, hence incompressible (Shannon).
The engine requires fair dice; fair dice outcomes cannot be conveyed
below their entropy; the "which pass" half of each outcome is the
unpayable remainder after the seed field pays the "which seed" half.
Conservation holds in every currency tested: stored bits, hit density,
match supply, carriage, structure (~2.5 free bits/record from the
explosion check — the only free source found; good for tens of passes).

## THE REQUIREMENTS CARD (attack this — June 2026)

Any mechanism claiming to solve stateless deep decode must deliver, for
every record: WHICH PASS made it, at a total cost under 2 bits per
record (the average win), subject to:

1. The file is written once — no per-pass rewriting reaches the decoder.
2. No content-awareness — the mechanism must work identically on random
   bytes (maintainer's content-blindness rule).
3. Deterministic decode — no search whose size grows with the file.
4. Costs count in EVERY currency: stored bits, hit density, match
   supply, wrap/carriage, or compute that scales with 2^bits.

Known no-go results it must evade (each priced this session):
- Stored tags/toggles: cost log2(passes) >= 2 bits beyond pass ~6.
- Global pass counter: 16 bits total cannot carry per-record answers.
- Depth/explosion inference: supplies ~2.5 bits/record (measured), the
  only free source found; insufficient alone beyond tens of passes.
- Digest verifier prefixes: density falls 2x per bit gained.
- Conventions (seed-pass agreement, freshness chains, pass-1-only):
  supply falls ~2x per bit gained (geometric starvation measured).
- Address/tree shuffles: make out-of-order opening harmless to
  positions; cannot carry the pass-varying salt component.
- Bits-back, ANS, CRDTs, reversible computing, trellis codes: each
  requires recoverability, pays full entropy, or is circular (surveyed).
- Core obstruction: births are dice outcomes; a uniform hash makes them
  independent and incompressible; deduction requires coupling and
  uniformity certifies there is none (singles are isolated unknowns).

The maintainer has overturned one impossibility claim in this project
before (the 2-bits-per-block total cap — wrong; the grinding channel
was real). This card exists so the next overturning, if it comes, takes
minutes to verify instead of nights.

## Cryptography sweep (complete, June 2026)

Checked in spirit against the requirements card: nonces/counter modes
(ship the nonce or ride transmission order - our order channel carries
placement); Signal ratchets (handle out-of-order by SHIPPING message
numbers); Merkle/accumulators (authenticate claims, cannot teach them);
trapdoors/RSA (gate access, create nothing); secret sharing/commitments
(reveal costs bits); steganography (needs slack; compression removes
it); syndrome coding (optimal sparse-pattern transmission: ~8 bits per
match at our density vs 2-bit wins - the priced floor, named);
time-lock/PoW (compute recovers only the derivable; births are not);
TMTO/rainbow tables (helps encoder search - already in spec); Diffie-
Hellman (needs two-way traffic; one-way DH does not exist).

Field-level conclusion: every crypto system that handles out-of-order
data ships sequence metadata; every one that avoids shipping enforces
strict order. Tagged or frozen - the same two machines. The empty cell
(out-of-order + no metadata + deterministic) is empty across their
field too.
