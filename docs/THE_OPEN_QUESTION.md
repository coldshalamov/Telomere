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
