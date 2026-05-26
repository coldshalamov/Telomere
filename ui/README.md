# Telomere — Operator Console

A desktop frontend for the Telomere generative compression engine. The UI is
a static HTML/CSS/JS bundle; it runs either as a Tauri 2 desktop app (with
the real engine bridged in via IPC) or as a plain web page (with a mock
engine for previewing the UI).

```
ui/
  index.html      single-file operator console markup, styles, bridge, mock mode

src-tauri/
  Cargo.toml      depends on the parent telomere crate by path
  tauri.conf.json frontendDist points at ../ui
  src/main.rs     #[tauri::command] handlers calling telomere::*
```

## Running as a desktop app (recommended)

Prerequisites: Rust toolchain (already required for Telomere) and the Tauri
v2 CLI. On Windows, WebView2 ships with Win11 so nothing else is needed.

```powershell
# one-time
cargo install tauri-cli --version "^2"

# dev mode (hot-reload the static frontend; rust changes require restart)
cd src-tauri
cargo tauri dev

# release build (writes a bundled .msi/.exe in src-tauri/target/release)
cd src-tauri
cargo tauri build
```

`cargo tauri build` requires an `icons/icon.png` (and optionally `.ico`, etc.)
in `src-tauri/icons/`. For `cargo tauri dev` icons are not strictly needed.

## Previewing the UI without Tauri

Open `ui/index.html` directly in a browser, or serve the `ui/` directory with
any static server (e.g. `python -m http.server` from `ui/`). The Tauri bridge
detection falls through to a deterministic mock engine that produces plausible
compression telemetry — useful for iterating on the UI without rebuilding the
Rust side.

## Wiring status

Implemented end-to-end against the real engine:

- `stat_file` — file metadata (name, size)
- `compress_file` — calls brute/v1, indexed/v2, or streaming/v2 based on the
  IPC config, writes a `.tlmr` next to the source, optionally
  roundtrip-verifies, and returns real candidate/literal/tier telemetry for v2
  engines, including tier work counters and streaming seed-scan counts.
- `decompress_file` — reads `.tlmr`, calls `telomere::decompress_with_limit`,
  writes the recovered bytes alongside
- `index_build`, `index_info`, `index_verify` — build and inspect exact-prefix
  seed expansion indexes from the index controls in the parameter bay. Verify is
  structural; accepted compression hits are still re-expanded and byte-checked
  by the engine.
- `research_artifacts` — reads generated docs JSON and returns compact
  evidence cards plus the current queue, held-out, exact-discovery, depth-4,
  and GPU gate summary for the operator ledger panel.

Host-side smoke coverage:

- `cargo test --manifest-path src-tauri/Cargo.toml` exercises streaming/v2
  telemetry serialization and indexed/v2 compression through the same engine
  dispatch used by the IPC commands, plus generated research artifact summary
  serialization.
- `python scripts/doc_lint.py` includes a structural smoke check that the UI
  evidence ledger still renders the queue, held-out, exact-discovery, depth-4,
  and GPU fields serialized by the Tauri bridge.

Pending frontend controls/instrumentation:

- Full per-layer/tier telemetry tables and exports.
- Streaming progress events from inside the engine loops.

These all live behind the same IPC schema (`CompressResult`); the engine
side now populates summary telemetry and a bounded selected-span lattice sample.
See `src-tauri/src/main.rs` for the exact shape the frontend consumes, and
`ui/index.html` `mockCompress()` for a worked example of the static-preview
path.

## Keyboard shortcuts

| Key       | Action              |
|-----------|---------------------|
| `1`       | Mode → Compress     |
| `2`       | Mode → Decompress   |
| `3`       | Mode → Verify       |
| `Enter`   | Execute current run |
