# Avenue H17 - original goal audit

Author: Codex continuation with independent subagent audit. Date: 2026-06-17.
Status: requirement audit after H15/H16; original-goal blocker identified.

## ORIGINAL GOAL

The active goal asks for:

```text
repeatable and stateless compression maintained over an arbitrary number of
passes, statistically on roughly all data, not reliant on structure
```

The main technical tensions were:

- salting/freshness helps match rate but creates birth/open/carry metadata;
- no salting risks saturation and falling match rate;
- sparse replacement needs open/carry maps or pass tags;
- any hidden final-board, checksum, pass-count, or profile-selection channel
  must be paid.

## SCOPE ASSUMPTIONS

This audit is not a claim that every Telomere-shaped idea is impossible. It is
conditional on the original content-blind goal:

- the codec and any interpreter/profile are fixed publicly before the file, or
  their selected IDs are paid in the final length;
- reconstruction is exact and lossless;
- decode is stateless and uniquely determined by the final stream plus the
  fixed/root/end header;
- every decoder-needed selector, pass count, schedule, checksum, public table,
  training choice, or adaptive prior is either independently public-fixed or
  included in the code length;
- the formal model for "not reliant on structure" and "roughly all data" is a
  uniform-source/content-blind hash law;
- there is no target-trained prior, oracle side channel, lossy decode, or
  uncharged adaptive interpreter.

## REQUIREMENT AUDIT

| Requirement | Status | Evidence | Result |
| --- | --- | --- | --- |
| Lossless/stateless decode | not disproven; solved mechanically in Total-Cover branch | `docs/SPEC_V1.md`, `docs/GOLDEN_CONFIG.md`, `TOTAL_COVER_RESULTS.md`, H5-H16 | Full rewrite means every record opens in order as `[arity][seed witness]`; no open/carry/birth channel is charged. H15 does not attack decode, only all-data savings. |
| Fresh recursive passes without birth metadata | solved only by Total-Cover invariant | H5-H16 | If every atom is rewritten every pass, all records are current-pass records; pass salt is decoder-derivable/fixed. |
| Paid witness stream | tested and still negative | H7-H14 | Raw delta, fixed slack, selected-order law, neutral capacity, joint partition, and public CRF all stay below zero after witness costs. |
| Maintained compression over arbitrary passes on roughly all uniform/content-blind data | impossible under stated premise | H2, H15 | Once final stream includes pass/profile/header selectors, recursive search is one lossless code; `Pr[L<=n-s] <= 2^-s`. |
| Not reliant on structure | incompatible with remaining escape | H16 | The only remaining escape is a non-uniform public interpreter/source prior, which is source-shaped by definition. |
| No reward-hacked hidden channels | enforced by ledgers | H2-H16 | Final boards, sparse maps, pass selectors, profile IDs, checksums, public tables, and priors are either charged or rejected. |

## SPEC CONTEXT

`docs/SPEC_V1.md` defines Telomere as generative seed-search compression and
makes the metadata contract explicit: decoder-derived values are not stored.
`docs/GOLDEN_CONFIG.md` already states the same high-level economics: decode and
bounded loss are working properties, while unaided random/content-blind data
sits far below the density threshold at every tested setting. `CLAUDE.md`
preserves the intended distinction: do not falsify the project with an
underpowered run, but also do not claim compression without the probability and
metadata ledger.

## KEY EVIDENCE

### Total-Cover solved the decode-order problem

Total-Cover changes sparse recursion into an ordered record stream:

```text
[arity][seed witness]
```

The decoder reads arity, reads the exact witness, expands it, and emits the
previous-layer atoms. Since no record is carried, there is no birth-pass/open
channel to transmit.

### Paid witness variants were near, but negative

The best explored high-arity branch is around:

```text
B=4, K=128, D=512
```

Representative paid misses:

| Branch | Best relevant result |
| --- | --- |
| H7 raw first-hit delta | about `-0.012` bits/input atom in stable rows |
| H9 fixed slack | near H7 in older rows, worse after exact-width/same-seed checks |
| H11 selected-order law | train-selected row negative; frozen `m8` negative |
| H12 neutral multiplicity | perfect future-credit upper bound still negative |
| H13 joint partition | `-0.013941` bits/input atom |
| H14 public CRF | `-0.015478` bits/input atom at N=128 |

These misses are small because high arity amortizes each negative record over
many atoms. They are not positive crossovers.

### H15 closes recursive best-of-pass under uniform law

For uniform `n`-bit input and any final uniquely-decodable stateless stream:

```text
Pr[L(X) <= n - s] <= 2^-s
E[L(X)] >= n
Pr[L(X) <= (1-epsilon)n] <= 2^(-epsilon*n)
```

Trying many passes or profiles does not escape this. If the decoder needs to
know which pass/profile won, those selector bits are part of `L(X)`. If the
selector is not paid, it is a hidden channel.

### H16 prices the only remaining premise change

If a public source prior `Q` makes `c` mass compress by `s` bits, then:

```text
Q(A_s)/U(A_s) >= c * 2^s
n - H(Q) >= d2(c || 2^-s)
```

Example:

```text
n=1024, s=128, c=0.90
average likelihood-ratio lift = 3.06e38
minimum entropy deficit = 114.731 bits
```

That can be valid source-shaped compression if the prior is real, but it is no
longer content-blind compression on roughly all arbitrary data.

## VERDICT

The original goal is internally inconsistent under the uniform/content-blind
interpretation of "roughly all data." Total-Cover solves stateless decoding,
but H15 proves that maintained recursive positive compression on roughly all
uniform inputs is counting-forbidden once every selector/header/profile channel
is paid.

This is a blocker for the original active goal, not a blanket death certificate
for Telomere. Work can resume if a premise changes or if an explicit flaw is
found in the H15 assumptions. The most important boundary is that a public
non-uniform interpreter may be legitimate compression for a real source, but it
is not the original content-blind "roughly all data" claim.

So the current state is:

```text
stateless decode problem: solved by Total-Cover
paid match/witness problem: tested deeply, near-miss but negative
recursive all-data content-blind goal: impossible by counting
```

## SCIENTIFICALLY HONEST NEXT GOALS

A next goal must change at least one premise:

1. **Source-shaped Telomere:** define a public non-uniform interpreter or seed
   universe and price its prior/profile honestly.
2. **Minority-win Telomere:** target a measurable minority of uniform inputs,
   with expansion on the rest, and report expected value honestly.
3. **Domain-control Telomere:** use planted/domain-shaped controls to prove
   codec/search/accounting behavior without claiming arbitrary-data
   compression.
4. **Practical hybrid:** combine ordinary source transforms with Telomere and
   clearly label the transform/prior as the compression source.
5. **Mechanism falsifier:** propose one explicit premise change, write its
   price ledger first, and test only if the expected-hit math is powered.

Without such a premise change, more public witness tables, pass schedules, or
recursive best-of-pass searches will only move the same entropy bill.
