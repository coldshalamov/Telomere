# ADR-0001: Keep Transform Preconditioners Outside `.tlmr` v1/v2

## Status

Accepted

## Context

Telomere's current compatibility contract is deliberately narrow:

- `.tlmr` v1 is one-layer-decodable Lotus preset 2.
- `.tlmr` v2 is recursive indexed/streaming Lotus preset 2.
- Decoding must not require a compression-time index or an external corpus.
- A Telomere seed-span match is valid only when
  `expand(seed)[0..span_len] == target_span`.

Recent generated evidence shows an important split:

- Raw seed-depth 1, 2, and opt-in 3 structured JSON controls still bloat and
  select zero spans.
- Cheap generic reversible transforms such as XOR residuals, subtraction
  residuals, and line transposition also select zero spans.
- A static JSON token preconditioner reduces effective bytes, but it still
  selects zero spans. That is domain-dictionary compression, not evidence of
  generative seed matching.

## Decision Drivers

- Protect `.tlmr` compatibility and index-free decompression.
- Keep benchmark claims honest and attributable.
- Avoid calling dictionary/preconditioner gains Telomere seed-span gains.
- Leave a clean path for future format versions if a transform becomes worth
  standardizing.

## Considered Options

### Option 1: Promote Transforms Into `.tlmr` v2

Pros:

- Could make transformed corpus wins look like end-to-end Telomere wins.
- Would let a decoder reconstruct transformed payloads automatically.

Cons:

- v2 has no transform descriptor today.
- Existing v2 files and docs would become ambiguous.
- Static token dictionaries would require versioned dictionaries or embedded
  tables.
- Current evidence does not show seed-span wins after generic transforms.

### Option 2: Keep Transforms As External Research Artifacts

Pros:

- Preserves v1/v2 compatibility.
- Keeps transform-only gains separate from seed-span gains.
- Lets research continue without prematurely freezing a weak format extension.

Cons:

- Transform experiments are not end-to-end `.tlmr` format features.
- Positive transform-only results need extra explanation.

### Option 3: Define A Future `.tlmr` v3 Transform Layer

Pros:

- Provides a principled path if a transform repeatedly wins.
- Could record transform kind, version, metadata, and dictionary identity.

Cons:

- Requires a new format version, golden vectors, corrupt-input tests, docs, and
  migration rules.
- Not justified by current generic-transform evidence.

## Decision

Keep transform preconditioners outside `.tlmr` v1 and `.tlmr` v2.

Transform experiments are research artifacts only. They may be measured in
`docs/TRANSFORM_SWEEPS.md`, but they are not part of supported compression or
decompression unless a future format version explicitly records transform
metadata and decoder behavior.

## Rationale

The current data says static domain tokens can reduce structured JSON bytes,
but the telemetry shows zero selected seed spans. That is useful compression
science, but it is not proof that the Telomere generative matcher found structure
in the corpus.

The cleanest research posture is to keep three ledgers separate:

- raw Telomere seed-span wins
- transform-only wins
- future hybrid candidates that combine both

## Consequences

Positive:

- `.tlmr` v1 and v2 remain unambiguous.
- Generated results can state exactly where savings came from.
- Future transform work has clear promotion criteria.

Negative:

- Static-token wins cannot be marketed as current Telomere format wins.
- Any production transform work will require a new format/version effort.

## Promotion Criteria

A transform can be proposed for a future `.tlmr` version only if it has:

- a reversible, deterministic specification
- enough metadata for index-free decompression
- generated golden vectors and corrupt-input tests
- generated corpus evidence that separates transform-only bytes from selected
  seed-span savings
- compatibility and migration rules in `docs/FORMAT.md` and
  `docs/RELEASE_CHECKLIST.md`

## References

- `docs/TRANSFORM_SWEEPS.md`
- `docs/VIABILITY.md`
- `docs/FORMAT.md`
- `docs/RESEARCH_PROGRAM.md`
