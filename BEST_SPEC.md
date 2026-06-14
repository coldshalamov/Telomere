# BEST_SPEC: Bounded Bundle Layer

Date: 2026-06-14

Status: strongest working candidate found so far. This is a finite constructive
extension, not an unbounded free channel. It keeps fresh salted opportunities
for many passes, decodes without per-record birth tags, and remains net-positive
on a dense reachable-bundle population after charging the birth/open ambiguity.

## Name

Bounded Bundle Layer (BBL)

## Purpose

Use only length-pinned bundle records during a bounded pass window. Avoid
arity-1 singles as the deep engine, because singles have no structural
open-pass subsidy and cost `log2(P)` bits per record. BBL accepts the finite
bundle subsidy as the birth/open channel and caps the pass count before that
subsidy is exhausted.

## State

- The live stream is an ordered list of self-delimiting items.
- An item is either a literal block or a bundle record.
- A bundle record replaces exactly `a >= 2` contiguous live items with one
  seed record.
- The layer has fixed public parameters:
  - block size `B`;
  - arity set, preferably one arity for the first candidate, `a = 2` or `a = 3`;
  - maximum passes `P_max`;
  - shuffle family;
  - hash/expander domain;
  - checksum width or equivalent root referee.

## Encode

For pass `t = 1..P_max`:

1. Scan the current packed stream for arity-`a` windows.
2. For each window at packed output position `j`, search compressive seed
   records.
3. A seed is eligible only if:
   - `expand(seed, t, j, a)` parses as exactly `a` self-delimiting items;
   - those items are byte-identical to the candidate window;
   - the seed record is shorter than the replaced window after all charged
     costs for the selected configuration.
4. Replace accepted non-overlapping windows greedily or by a deterministic
   selector.
5. Shuffle the packed stream with the public reversible shuffle.

Salt rule:

```text
salt = H_domain(layer_id, pass_index t, packed_record_position j, arity a)
```

The salt uses the packed record coordinate, not the pre-replacement hole
coordinate. This matters: the packed coordinate is what the reverse decoder can
observe after unshuffling.

Stop rule:

- For the candidate kernel, run a fixed `P_max`.
- For a production variant, a no-hit pass may stop the layer, but the stop
  condition must be derivable by reverse trial decode or stored as fixed/root
  layer data and priced.

## Wire

Store:

- fixed/root header fields needed by the base Telomere format;
- layer parameters if not profile-fixed;
- final packed item stream;
- original length;
- fixed checksum/root referee.

Do not store per-record birth pass, per-record open/carry bit, hole coordinates,
or per-pass mutation logs.

## Decode

Input: compressed bits plus fixed/root/end-state data.

For pass `t = P_max..1`:

1. Unshuffle the packed stream using the public inverse shuffle.
2. Walk the unshuffled stream.
3. For each literal, carry it.
4. For each record at packed position `j`, branch:
   - carry it unopened;
   - open it using `expand(seed, t, j, a)`, but only if the prefix parses as
     exactly `a` self-delimiting items.
5. Prune branches whose item count exceeds the original length or whose grammar
   is invalid.

After all reverse passes:

1. Keep candidates that are all literals and have the original length.
2. Use the fixed checksum/root referee to select the original.

The checksum is not free in the ledger. Its role is equivalent to selecting one
surviving reading among the parse-valid open/carry branches. The priced
asymptotic birth/open cost for `R` final bundle records is:

```text
ambiguity_bits = R * c_a(P_max)
c_a(P) = log2(1 + (P - 1) * 2^-E_a)
```

where `E_a = -log2(q_a)` and `q_a` is the wrong-salt parse-survival probability
for arity `a`.

## Freshness

BBL refreshes hash opportunities because each pass changes at least one of:

- pass index `t`;
- packed position `j`;
- neighboring item windows after shuffle.

Therefore the same logical content can receive fresh effective SHA outputs on
later passes while the decoder can still reconstruct the correct salt when it
opens the record at the tested reverse pass.

## Accounting

Per accepted bundle record:

```text
net_per_bundle = replaced_bits - record_bits - c_a(P_max)
```

For the Golden-style measured bundle ledger:

| arity | `E_a` bits | `P` with `c_a(P) < 2` | `c_a(64)` |
| --- | ---: | ---: | ---: |
| 2 | 9.36 | about 1,972 | 0.132 |
| 3 | 12.59 | about 18,497 | 0.015 |
| 4 | 14.97 | about 96,282 | 0.003 |
| 5 | 18.20 | about 903,374 | near 0 |

This gives a real bounded win in a dense reachable-bundle regime. Example:
with arity 2, `P = 64`, and gross selected-record win `2.17` bits, the charged
birth/open cost is `0.132` bits, leaving about `2.038` bits per accepted bundle
before fixed header amortization. For a dense generated corpus with many
accepted bundles and few leftovers, this is net-positive.

Whole-file caveat:

BBL does not make random data compress. Literal carriage and low base hit
density still dominate random/content-blind inputs. The candidate wins only in
the explicitly stated dense reachable-span regime: a population where exact
bundle windows are frequent enough that selected bundle savings exceed literal
carriage, fixed header, and ambiguity costs.

## Kernel

Runnable toy:

```powershell
python model_analysis\birth_channel_research\bounded_bundle_codec.py
```

The toy uses:

- 4-bit literals;
- fixed arity 2;
- 5-bit seeds;
- incomplete item grammar;
- SHA-256 expansion keyed by `(pass, packed_position, seed)`;
- reversible shuffle;
- DFS reverse decoder with no birth tags.

The default run now prints two fixtures:

- a random mechanics fixture, which round-trips over six passes and shows fresh
  matches but does not compress;
- a generated dense reachable-bundle fixture, which round-trips over two passes
  and is payload-positive after ambiguity pricing.

Current generated dense fixture output:

```text
blocks=24, passes=2
matches=13
payload_delta=+19.000 bits
asymptotic_delta=+11.918 bits after ambiguity pricing
charged_delta=-54.082 bits after the 66-bit toy header
```

This is the first concrete positive-control regime for BBL: the codec round
trips, the decoder receives no birth tags, and the dense generated population is
positive before fixed header amortization. It is still not a natural-density
claim. At larger scale or with chunked dense blocks sharing fixed/root data, the
header is amortized once the dense population supplies more than the fixed
referee/header bits.

## Mutations Tried

- Pre-replacement anchor salt: failed in the toy because the packed decoder sees
  the record at its post-replacement packed coordinate. Fixed by salting with
  packed record position.
- Arity-1 singles: rejected as the deep engine because every wrong salt still
  parses as one item, giving exact ambiguity `P^R`.
- Final-position board: mechanically reversible when positions are stored, but
  the final arrangement note is the birth channel and costs `log2(valid final
  states)`.
- Biased seed/pass grammar: can encode birth bits in seed classes, but each bit
  costs at least one bit of match supply.

## TODO

1. Replace the toy arity-2 grammar with the real SPEC_V1/Lotus cost table in a
   small BBL kernel.
2. Upgrade the generated dense fixture from "payload/asymptotic positive" to
   fully charged positive after fixed/root header amortization, with a chunking
   rule whose own boundaries are priced.
3. Implement a bounded decoder with an explicit branch budget derived from
   `R * c_a(P)` rather than a generic state cap.
4. Test arity 3 and arity 4 variants; they have much larger pass windows but
   lower natural hit supply.
5. Price whole-layer literal carriage for several dense regimes and identify
   the minimum accepted-bundle density needed for a kept layer.
6. Decide whether BBL is a Telomere mode or a hybrid/dense-class mode. Under
   strict content-blind random input, it is not a universal compressor.
