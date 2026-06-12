# Telomere — Repo Alignment & Cleanup Instructions

**For: a cleanup agent running deterministically inside this repo.**
**Authority: `docs/FORMAT_CANONICAL.md` is the single source of truth.** Your job
is to make the code, docs, and measurements agree with it, and to remove
accumulated bloat — without destroying the honest evidence record or guessing at
the maintainer's open decisions.

This repo drifted because a prior goal-loop agent resolved format questions by
picking which of two disagreeing files to trust (see `.agent/brain/DECISIONS.md`,
which records exactly that). Do not repeat that pattern. When code and a doc
disagree, **`FORMAT_CANONICAL.md` wins**; when `FORMAT_CANONICAL.md` is silent or
marked **[CONFIRM]**, **stop and ask the maintainer** — do not invent an answer.

---

## Guardrails (read before doing anything)

1. **Git is the safety net. Never hard-delete.** Remove files only with
   `git rm` (recoverable from history) or by moving them into `docs/_archive/`.
   Make one commit per phase with a clear message. Never `git push --force`,
   never rewrite history, never empty the trash.
2. **List before you remove.** For every deletion phase, first write the full
   candidate list to `docs/CLEANUP_MANIFEST.md` with a one-line reason each, then
   stop and let the maintainer approve before executing.
3. **Tests gate every phase.** `cargo test --all-targets` must pass before you
   start and after each phase. If a change breaks a test, fix the change, not the
   test. Never add `#[ignore]` to make the suite green.
4. **Do not touch the honest record.** `VIABILITY.md`, `THEORY.md`,
   `POWER_MODEL.md`, `RESULTS.md`, `CLAUDE.md`, `AGENTS.md`, `FORMAT_CANONICAL.md`,
   and everything under `model_analysis/` stay. The zeros and the bloating
   controls are evidence, not bloat.
5. **Never report a format "aligned" without a golden round-trip.** See Phase 5.

---

## Phase 1 — Align the wire format to canonical (the one load-bearing fix)

Goal: replace the drifted **J1D1** arity encoding with the canonical Kraft-complete
arity alphabet from `FORMAT_CANONICAL.md` §2.

1. In `src/header.rs`: replace the arity field codec. Today it routes arity
   through `LOTUS_ARITY_J_BITS=1 / LOTUS_ARITY_TIERS=1` (J1D1), spending
   `{3,5,5,5,5,6}` bits on arity 1–5 + literal. Implement the canonical alphabet
   instead:

   | arity | codeword | bits |
   |------:|:--------:|:----:|
   | 1 | `00` | 2 |
   | 2 | `01` | 2 |
   | 3 | `100` | 3 |
   | 4 | `101` | 3 |
   | 5 | `110` | 3 |
   | literal | `111` | 3 |

   Encode/decode this as a direct prefix-free code (selector bit + 1–2 bit
   field), not via the generic integer codec. Update `v1_record_bit_len`,
   `encode_v1_record_into_writer`, `decode_v1_record_from_reader`, and the
   `small_indices_are_compact` / `literal_marker_bit_len` tests to the new
   widths (literal is **3 bits**, not 6; arity-1 seed-0 record is now
   `2 + |Lotus seed|` bits).

2. Align the **seed-index** field to **J3D1** (jumpstarter 3, one tier), the
   confirmed canonical design (`FORMAT_CANONICAL.md` §4). The code currently runs
   `LOTUS_J_BITS=3, LOTUS_TIERS=2` (J3D2). **Before changing the constants you
   must obtain the `lotus` sibling crate (`../lotus/src/lib.rs`, not present in
   this checkout) and confirm bit-for-bit which `(J_BITS, TIERS)` emits the
   five-field J3D1 layout** — do not assume `TIERS=1` without checking the
   crate's tier convention. Pin the confirmed encoding with a golden vector. If
   you cannot obtain the crate, stop and report; do not guess.

3. Reconcile `docs/FORMAT.md` to match: its "arity value = 5 / 0..=4" literal
   description is the same drift. Update it, or replace its record-format section
   with a pointer to `FORMAT_CANONICAL.md` so there is one description, not two.

4. Confirm the EOF logic is **unchanged** — it is already correct
   (`FORMAT_CANONICAL.md` §6): decode records until `bytes_out == original_len`,
   then verify zero pad to `payload_bit_len`. Do not "fix" it. Only re-verify it
   still holds after the arity change.

---

## Phase 2 — Unify v1/v2 (only if maintainer approves; otherwise skip)

The repo carries two record formats (v1 two-field arity records; v2 three-field
`tag/span_len/seed_index` records). Canonical intent is **one** recursive format
(`FORMAT_CANONICAL.md` §7, [CONFIRM]). This is a larger change. Do **not** attempt
it in the same pass as Phase 1. Write a short migration proposal, get explicit
approval, then do it as its own gated task with its own golden vectors.

---

## Phase 3 — Inventory and remove bloat (list-before-delete)

The repo's own contract (`AGENTS.md`, "Do not check in massive low-level
generated JSON row matrices as if they were source… treat bulky experiment
matrices as reproducible build artifacts") authorizes this. Apply these
categories; write every candidate to `docs/CLEANUP_MANIFEST.md` and pause for
approval before removing.

**Remove from git (regenerable; keep the generator scripts):**
- Generated evidence matrices: the large `docs/*.json` artifacts listed in
  `VIABILITY.md`'s "Source Artifacts" (e.g. `source_family_cross_validation.json`
  ~263 KB, `research_artifacts_snapshot.json`, the per-probe `*.json`). Keep the
  human-readable `.md` ledgers that summarize them; the raw row matrices are
  build output.
- `docs/candidate_runtime_verification/*.txt` command-output dumps.
- One-off probe write-ups that were superseded — but **only** those a `git log`
  shows were produced by the goal-loop and never referenced again. When unsure,
  archive to `docs/_archive/`, don't delete.

**Gitignore (should never have been committed):**
- `target/`, `src-tauri/target/` (build artifacts — large).
- `scripts/__pycache__/`, `**/*.pyc`.
- `.serena/cache/` (e.g. the ~508 KB `.pkl`).
Add these to `.gitignore`, then `git rm -r --cached` them (keeps them on disk,
drops them from the repo).

**Identify the goal-loop pollution specifically:**
- Read `.agent/brain/DECISIONS.md` and `MISTAKES.md` and `git log --oneline`
  for the relevant window. Flag commits/files attributable to the Codex
  goal-loop. List them in the manifest with the commit hashes. Do not bulk-revert
  — surface them for the maintainer to confirm, since some may contain real work.

**Keep, always:** `src/`, `tests/`, the canonical docs (§Guardrail 4),
`Cargo.toml`, `.github/`, the architecture/format/research docs that are
hand-written rather than generated.

---

## Phase 4 — Re-measure on the corrected format

**Every number currently in the ledgers was measured on the drifted J1D1
format.** After Phase 1 lands, regenerate the core measurements so the record
matches reality:

1. Re-run the planted positives (`planted-sha256-arity2`, the span8/span12
   fixtures) and confirm they still round-trip and still show negative delta —
   they should improve slightly (cheaper literal/arity codewords).
2. Re-run the random and PDF controls. Expected: they still bloat, but **less**
   — the literal tax drops from 6→3 bits per marker, so e.g. the ~+8% random
   control at B=8 should shrink toward ~+4.7%. Record the new numbers.
3. Update `VIABILITY.md` / `RESULTS.md` via their generator scripts (not by
   hand), so the ledgers stay generated-and-honest.
4. Do **not** re-run broad natural-corpus searches — `CLAUDE.md` and the
   search-frontier gate say they're underpowered and that's settled. Cleanup
   does not reopen the viability question.

---

## Phase 5 — Verify (required before declaring done)

1. `cargo fmt --all -- --check`, `cargo clippy --all-targets -- -D warnings`,
   `cargo test --all-targets` all green.
2. **Golden round-trip:** compress → decompress a set of fixtures (empty file,
   1 byte, a partial-final-block file, a planted file, a random file) and assert
   byte-exact recovery and `hash == output_hash`. Add any missing case as a
   committed test.
3. **Format invariants** from `FORMAT_CANONICAL.md` §6: assert
   `file_len == 5 + ceil(header_bits/8) + ceil(payload_bit_len/8)`, the literal
   codeword is 3 bits, and decode halts exactly at `bytes_out == original_len`
   with all trailing pad zero.
4. Write `docs/CLEANUP_REPORT.md`: what changed, what was removed (with reasons),
   the before/after header and control sizes, and every open [CONFIRM] still
   awaiting the maintainer.

---

## Do NOT

- Do not delete anything not first listed in `CLEANUP_MANIFEST.md` and approved.
- Do not change the seed codec, unify v1/v2, or alter EOF logic without explicit
  approval — EOF is already correct.
- Do not "improve" the evidence ledgers' conclusions, soften the bloating
  controls, or touch `CLAUDE.md`/`AGENTS.md`/`model_analysis/`.
- Do not reopen or re-litigate the compression-viability question. Your scope is
  alignment and tidiness, full stop.
- Do not guess on any [CONFIRM] item. Collect them and return them to the
  maintainer.
