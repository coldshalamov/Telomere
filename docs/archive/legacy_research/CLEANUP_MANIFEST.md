# Cleanup Manifest

No removals have been executed. This manifest is the Phase 3 list-before-delete
checkpoint and requires maintainer approval before any `git rm`, archive move,
or cached-file cleanup.

## Remove from git candidates

| Path | Reason |
| --- | --- |
| `docs/source_family_cross_validation.json` | Generated raw source-family matrix from `59b998c`; summarized by `docs/SOURCE_FAMILY_CROSS_VALIDATION.md` and regenerable by `scripts/generate_source_family_cross_validation.py`; currently referenced by `scripts/doc_lint.py`, so removal requires follow-up lint adjustment. |
| `docs/research_artifacts_snapshot.json` | Generated compact artifact snapshot retained by `f59a2a1` after broader JSON bloat removal; `docs/GENERATED_LEDGER_PIPELINE.md` and `src-tauri/src/main.rs` reference it, so removal requires confirming the UI/reporting path should not keep this runtime input. |
| `docs/agent_reports/manifest.json` | Generated research-agent registration manifest from `b1a5d6a`; referenced by research-agent intake docs/scripts, so remove only if that lane is retired or archived. |
| `docs/agent_reports/report_templates.json` | Generated research-agent template matrix from `b1a5d6a`; referenced by `docs/agent_reports/REPORT_TEMPLATES.md`, so remove only with the agent-report lane. |
| `docs/candidate_runtime_verification/01-cargo-fmt-all-check.txt` | Generated command-output dump from `b1a5d6a`; stale runtime evidence should be regenerated, not kept as source. |
| `docs/candidate_runtime_verification/02-cargo-fmt-manifest-path-src-tauri-cargo-toml-check.txt` | Generated command-output dump from `b1a5d6a`; stale runtime evidence should be regenerated, not kept as source. |
| `docs/candidate_runtime_verification/03-cargo-clippy-all-targets-d-warnings.txt` | Generated command-output dump from `b1a5d6a`; stale runtime evidence should be regenerated, not kept as source. |
| `docs/candidate_runtime_verification/04-cargo-test-all-targets.txt` | Generated command-output dump from `b1a5d6a`; stale runtime evidence should be regenerated, not kept as source. |
| `docs/candidate_runtime_verification/05-cargo-check-features-gpu-all-targets.txt` | Generated command-output dump from `b1a5d6a`; stale runtime evidence should be regenerated, not kept as source. |
| `docs/candidate_runtime_verification/06-cargo-check-manifest-path-src-tauri-cargo-toml.txt` | Generated command-output dump from `b1a5d6a`; stale runtime evidence should be regenerated, not kept as source. |
| `docs/candidate_runtime_verification/07-cargo-test-manifest-path-src-tauri-cargo-toml.txt` | Generated command-output dump from `b1a5d6a`; stale runtime evidence should be regenerated, not kept as source. |
| `docs/candidate_runtime_verification/08-python-scripts-doc-lint-py.txt` | Generated command-output dump from `b1a5d6a`; stale runtime evidence should be regenerated, not kept as source. |
| `docs/candidate_runtime_verification/09-python-scripts-generate-evidence-regimen-py-check.txt` | Generated command-output dump from `b1a5d6a`; stale runtime evidence should be regenerated, not kept as source. |
| `docs/candidate_runtime_verification/10-python-scripts-generate-research-ledgers-py-check.txt` | Generated command-output dump from `b1a5d6a`; stale runtime evidence should be regenerated, not kept as source. |

## Archive or confirm candidates

| Path | Reason |
| --- | --- |
| `.agent/brain/DECISIONS.md` | Goal-loop state file from `47e4c25`; contains the format-choice record cited by cleanup instructions, so archive rather than delete if approved. |
| `.agent/brain/MISTAKES.md` | Goal-loop state file from `47e4c25`; not source or canonical documentation. |
| `.agent/brain/NEXT.md` | Goal-loop state file from `47e4c25`; not source or canonical documentation. |
| `.agent/brain/PLAN.md` | Goal-loop state file from `47e4c25`; not source or canonical documentation. |
| `.agent/brain/PROJECT.md` | Goal-loop state file from `47e4c25`; not source or canonical documentation. |
| `.agent/brain/QUESTIONS.md` | Goal-loop state file from `47e4c25`; not source or canonical documentation. |
| `docs/agent_prompts/agent-acceleration-acceleration.prompt.txt` | Generated agent prompt from `b1a5d6a`; archive/remove only if research-agent prompt lane is retired. |
| `docs/agent_prompts/agent-compute-economics-compute-economics.prompt.txt` | Generated agent prompt from `b1a5d6a`; archive/remove only if research-agent prompt lane is retired. |
| `docs/agent_prompts/agent-corpus-transform-corpus-transform.prompt.txt` | Generated agent prompt from `b1a5d6a`; archive/remove only if research-agent prompt lane is retired. |
| `docs/agent_prompts/agent-format-policy-format-policy.prompt.txt` | Generated agent prompt from `b1a5d6a`; archive/remove only if research-agent prompt lane is retired. |
| `docs/agent_prompts/agent-meta-research-meta-research.prompt.txt` | Generated agent prompt from `b1a5d6a`; archive/remove only if research-agent prompt lane is retired. |
| `docs/agent_prompts/agent-operator-ui-operator-ui.prompt.txt` | Generated agent prompt from `b1a5d6a`; archive/remove only if research-agent prompt lane is retired. |

## Local build/cache cleanup candidates

These are not tracked by git. If approved, remove locally and keep/confirm ignore
coverage; no history rewrite is involved.

| Path | Current state | Reason |
| --- | --- | --- |
| `target/` | Ignored by `.gitignore`; about 43,410 files / 11,406,011,920 bytes locally. | Rust build artifacts. |
| `src-tauri/target/` | Ignored by `src-tauri/.gitignore`; about 7,421 files / 3,339,537,476 bytes locally. | Tauri/Rust build artifacts. |
| `scripts/__pycache__/` | Ignored by `.gitignore`; about 107 files / 3,622,771 bytes locally. | Python bytecode cache. |
| `.serena/cache/` | Ignored by `.gitignore`; about 1 file / 508,641 bytes locally. | Tool cache. |

## Goal-loop provenance for maintainer review

The following commits are suspected goal-loop/prototype-era pollution or broad
generated-artifact churn. This is not a bulk-revert list; it is provenance for
reviewing candidates above and any future archive decisions.

| Commit | Reason to review |
| --- | --- |
| `47e4c25` `Add project docs and update compression logic` | Added `.agent/brain/*` and recorded the drift-prone "Lotus 4-Field" decision. |
| `9f426f1` `M0: Real hasher, gitignore fix, arity/config cleanup, stale test removal` | Early goal-loop implementation churn touching header/compression/test format surfaces. |
| `5c3e846` `M1: Rayon-parallel find_seed_match + fix slow tests for real hasher` | Early goal-loop implementation/test churn. |
| `0ed761f` `Fix decompress/validation/safety tests: SHA256->BLAKE3 + fast config` | Early goal-loop test churn. |
| `1245cae` `Fix CLI, memory check, and remaining test suite issues` | Early goal-loop CLI/test churn. |
| `87c585a` `Fix SHA256 expander, header tests, and CLI test configs` | Early goal-loop hasher/header/test churn. |
| `5351c12` `Fix GPU tests, finalize 106-test green suite` | Early goal-loop test churn. |
| `15b4713` `Add research plan, task checklist, and docs from Grok` | Adds non-canonical planning/docs material; review only, do not remove without approval. |
| `a763d63` `M2: Per-pass delta stats, JSON output, RunSummary, gpu tests ignored` | Early goal-loop stats/test churn; note current rules forbid adding ignored tests. |
| `f46394c` `Clippy clean: zero warnings across lib and bins` | Early cleanup commit in the same window. |
| `2cefa11` `Improve convergence detection in compress_multi_pass_with_config` | Early compression behavior change in the same window. |
| `b1a5d6a` `feat(research): integrate Lotus v2 streaming proof stack` | Added most current agent prompt/report/runtime-output artifacts and many generated JSONs later removed by `f59a2a1`. |
| `59b998c` `feat(research): cross-validate source preset wins` | Added `docs/source_family_cross_validation.json`, the largest currently tracked JSON matrix. |
| `f59a2a1` `Remove generated research ledger bloat` | Removed most generated JSON matrices and retained the two current top-level JSON exceptions. |

## Existing ignore notes

- `.gitignore` already ignores `/target`, `.serena/`, `__pycache__/`, `*.pyc`, and `docs/*.json`.
- `.gitignore` currently exempts `docs/research_artifacts_snapshot.json` and `docs/source_family_cross_validation.json`; remove those exceptions only if the corresponding tracked JSON files are approved for removal.
- `src-tauri/.gitignore` already ignores `/target` inside `src-tauri/`.
