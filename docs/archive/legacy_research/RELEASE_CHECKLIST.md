# Production Release Checklist

Telomere is not production-ready until every item below is true for the release
candidate. This checklist separates core software gates from research-evidence
regeneration so release hygiene does not become unbounded experiment churn.

## Format Support

- Supported file format is documented in `docs/FORMAT.md`.
- `format_version`, `lotus_preset`, seed enumeration order, public-preset ids,
  and hasher semantics are fixed for the release.
- Golden byte-vector tests pass for v1 headers, v2 descriptors, Lotus
  arity/literal fields, seed index boundaries, and public-preset descriptors.
- `.tlmr` files decode without Python sidecars or external hidden dictionaries.

## Compatibility Guarantees

- The release states whether it can read previous `.tlmr` versions.
- The release states whether files written by this version are guaranteed to be
  readable by future versions.
- Any incompatible change bumps `format_version`.
- Any Lotus record change bumps `lotus_preset`.
- Any hasher semantic change gets a new `hasher_kind` id.
- Any transform/preconditioner support requires a versioned transform descriptor
  or a new file format version; external transform experiments are not release
  format support.

## Current Compatibility Policy

- `.tlmr` v1 is the only production-candidate format line.
- `.tlmr` v2 is experimental: it can be decoded by the current repo, but it is
  not yet a long-term compatibility promise.
- Pre-v1 experimental headers are unsupported unless a standalone migration tool
  explicitly recognizes and rewrites them.
- Future production releases must keep v1 decode support or provide a standalone
  migration tool before removing it.

## Known Limitations

- `.tlmr` v1 is one-layer-decodable only.
- Recursive multi-pass output is supported only for indexed/streaming `.tlmr`
  v2 files.
- Random data is expected to bloat.
- Seed depth 3 is expensive and not used in normal tests.
- GPU is research-only and not a production acceleration path.
- v2 index building is CPU/RAM oriented; GPU/ASIC streaming lookup remains
  research-only.
- Transform/preconditioner sweeps are research-only unless a release explicitly
  documents transform metadata, inverse decoding, and dictionary identity.

## Core Verification Gates

Run these before a release tag or before claiming the checked-in software is
healthy:

```powershell
cargo fmt --all -- --check
cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo check --features gpu --all-targets
cargo check --manifest-path src-tauri/Cargo.toml
cargo test --manifest-path src-tauri/Cargo.toml
python scripts/doc_lint.py
```

## Research Evidence Gates

Generated evidence gates are on-demand audit tools, not default release chores.
Run them only when a source change touches the relevant generator, fixture,
format policy, public preset, corpus definition, evidence summary, or UI
snapshot.

Important examples:

```powershell
python scripts/generate_source_family_cross_validation.py --check
python scripts/generate_candidate_runtime_verification.py --check
python scripts/generate_evidence_regimen.py --print-plan
python scripts/generate_evidence_regimen.py --check
```

If a generated row matrix is needed for audit, regenerate it locally, inspect
the Markdown summary and compact evidence snapshot, and leave bulky JSON out of
git unless the user explicitly asks to preserve that raw artifact.

## Artifact Regeneration

If a compact checked-in artifact is stale, regenerate the narrow artifact that
owns it and inspect the diff. Prefer targeted checks over the full evidence
regimen.

Use the full regimen only when changing generator dependencies across multiple
families:

```powershell
python scripts/generate_evidence_regimen.py
```

If a long run fails after several slow probes, resume from the failing key
printed in the error:

```powershell
python scripts/generate_evidence_regimen.py --start-at <key>
```

Print the order before manual review or partial reruns:

```powershell
python scripts/generate_evidence_regimen.py --print-plan
```

## Claim Boundary

Passing these gates does not prove universal compression, production
acceleration, raw natural-corpus viability, or recursive convergence. Release
notes must say exactly which evidence class passed: implementation proof,
accounting proof, throughput calibration, control result, native `.tlmr`
negative delta, or powered thesis-scale evidence.
