# Telomere — Table of Record

*One verdict per idea. Final as of June 2026. A row changes only with
named evidence attached. This table exists to end referent-drift: every
discussion should name its row.*

| # | idea | verdict | status |
| - | --- | --- | --- |
| 1 | Egg carton / slot table (fixed slots, blocks never shift) | Solves count-corruption; all slot histories computable by arithmetic | PROVEN (36/36 harness) |
| 2 | Scratchpad pass counter | Gives total passes; cannot carry per-record births | SETTLED |
| 3 | Bundling across empty slots | Works; skip-to-next-occupied derivable; freshness intact | SETTLED |
| 4 | Record decode (Lotus, arity, dangling bits) | Works exactly as the maintainer described | PROVEN |
| 5 | Singles' placement | Never needs birth info (home = full reversal) | PROVEN |
| 6 | Singles' salts — THE ATOM | Home-slot salt: decodes forever, dice frozen. Moving salt: fresh dice, birth needed. No third option found | SETTLED |
| 7 | Depth / explosion check | ~2.5 free bits per record (true expansions terminate; wrong-salt ones explode) | MEASURED |
| 8 | Toggle / written pass numbers | Decodes 100%; costs log2(passes)/record; net positive only ~passes 1-6 | PRICED |
| 9 | Conventions (seed-pass rule, freshness chain, pass-1-only) | Decode free; paid in match supply; geometric starvation | PRICED |
| 10 | Bundle birth at depth, at zero cost | **OPEN — the wall.** Every other row avoids it or pays for it | OPEN |
| 12 | Placement channel — final form: maintainer's x2 / x2+1 rule (match -> even slot, miss -> odd) | Fully invertible, no deadlock: the slot number's trailing binary digits ARE the match history (the address becomes the diary). Cost: addresses grow 1 bit per block per pass; the wire pays for addresses; exact par with tags. The three pockets of a file (items, header, arrangement) are now ALL tested: the bill follows at par into each. No fourth pocket exists | PRICED — exact |
| 11 | Whole machines | Fresh-salts-unpaid: ~0.06%/pass sustained, undecodable at depth. Any paying variant: decodable, lifetime <~0.3%, never repays the 37.5% wrap | SETTLED |

Supporting detail: SPEC_V1.md (the machine), GOLDEN_CONFIG.md (the
parameter study), THE_OPEN_QUESTION.md (row 10 in full, with the
requirements card and the literature survey), TELOMERE_RESULT_LEDGER.md
(history and corrections).
