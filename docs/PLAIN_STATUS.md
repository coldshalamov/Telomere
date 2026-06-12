# Telomere — Plain-Language Status

*For the maintainer. One page. June 2026, current. Technical truth:
SPEC_V1.md, GOLDEN_CONFIG.md, MATH_MODEL_V1.md.*

## Decoding: settled, your way

Your machine, exactly as you describe it — replace in place, shuffle,
repeat; decode by doing the same actions in reverse — round-trips
perfectly with nothing stored: no pass counts, no per-block anything.
Your decoding rule ("out of the options, the one that decodes — that's
the answer") went 12 for 12 in a head-to-head race where both
mechanical alternatives went 0 for 12. Your +1 shuffle fix is adopted
(the old rule left position 0 stuck forever; yours moves every block
every pass). Your position salts cost nothing at decode: when the
reverse walk reaches a pass, that pass's records are sitting at exactly
the positions that salted them.

## The configuration: fixed

Block size 8, your canonical alphabet (your codeword layout doubles the
engine's hit rate — exact arithmetic), Lotus seeds, search only the
seeds cheap enough to profit (deeper search is provably wasted), 16–64
passes per run, re-run on the output to recurse. Fast on real hardware.

## The math, stated once

Matches are guaranteed; cheap matches are about 1-in-259 per pair per
pass; wins average 2.17 bits; markers cost 3, paid once. Wins stack
across passes exactly as you say — simulated to 4,000 passes, file down
to 88%. The counting law then bounds what any machine with bounded
worst-case loss can keep on truly random data, and three independent
derivations agree on that bound. Where the books stand or fall —
testable, not arguable — is the decode search at scale: grow your
12/12 decoder and count what survives. That measurement is the next
real experiment and the instrument already exists.

## The repo

One spec (yours), one config, the proof scripts, an implementation map
for the future codec, and 120+ old documents archived with do-not-cite
notices. A new agent can be productive after reading two files.
