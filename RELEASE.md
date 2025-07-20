# Release Checklist

Follow this checklist before publishing a new Telomere release.

- [ ] `cargo clippy --all-targets -- -D warnings`
- [ ] `cargo test --release` for all supported targets
- [ ] `cargo deny check`
- [ ] Run fuzz harnesses for 72h with no crashes
- [ ] Build release binary and record SHA-256 hash
- [ ] Document reproducible build steps
