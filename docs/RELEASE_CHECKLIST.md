# Production Release Checklist

Telomere is not production-ready until every item below is true for the release
candidate.

## Format Support

- Supported file format is documented in `docs/FORMAT.md`.
- `format_version` is fixed for the release.
- `lotus_preset` is fixed for the release.
- Seed enumeration order is unchanged.
- Golden byte-vector tests pass for the file header, Lotus arity/literal fields,
  and seed index boundaries.

## Compatibility Guarantees

- The release states whether it can read previous `.tlmr` versions.
- The release states whether files written by this version are guaranteed to be
  readable by future versions.
- Any incompatible change bumps `format_version`.
- Any Lotus record change bumps `lotus_preset`.
- Any hasher semantic change gets a new `hasher_kind` id.

## Known Limitations

- `.tlmr` v1 is one-layer-decodable only.
- Recursive multi-pass output is not supported.
- Random data is expected to bloat.
- Seed depth 3 is expensive and not used in normal tests.
- GPU is research-only and not a production acceleration path.

## Migration Rules

- Do not silently reinterpret old headers.
- Reject newer unsupported `format_version` values.
- Reject unsupported `lotus_preset` values.
- Preserve hasher metadata during any rewrite.
- Provide a standalone migration tool before changing existing file semantics.

## Verification Gates

Run all of these before a release tag:

```powershell
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo check --features gpu --all-targets
python scripts/doc_lint.py
python scripts/generate_results.py
```

After regenerating results, inspect `docs/RESULTS.md` and `docs/results.json`
for unexpected changes before committing them.
