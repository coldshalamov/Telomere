# Deprecated model artifacts (kept for provenance, OFF the active proof path)

Moved here by the truth-surface alignment task. Do not cite these in new work;
the active path is `../telomere_math_model.py` (+ validator, CSV, reports,
`METHODS_APPENDIX.md`) and `proof_kernel/`.

| file | why deprecated |
| --- | --- |
| `FINDINGS.md` | Written against the drifted-era costs (J1D1 6-bit literal / V1-vs-V2 gap framing) and pre-canonical break-even constants (824x/3066x). Superseded by `METHODS_APPENDIX.md` + `telomere_math_report.md` on canonical costs. |
| `arity_floor.py` | Arity-as-a-dial toy: applied a uniform `max(3,bitlen(A)+1)` arity code to ALL arities (1 bit off canonical at A∈{1,2,5}) and swept arity far beyond the spec'd 1..5 alphabet. Reconciliation table lives in `METHODS_APPENDIX.md` §6.3. |
| `breakeven_landscape.py` | Early depth/density two-axis sketch using a fixed gap constant rather than exact canonical record costs; superseded by `telomere_math_model.py`'s `M_{a,D}(r)` machinery. |
| `recurrence_model.py` | Mean-field recurrence (entry lengths collapsed to an average, constant 2.17-bit win). Explicitly superseded by the histogram/distribution model. |
| `public_dictionary_benchmark.py` (+ results `.txt`) | Dictionary detour — not part of the Telomere mechanism (seed search + Lotus records only). Quarantined on maintainer instruction. |
| `trained_enum_test.py` | Rank/frequency-table detour — same reason; expressly rejected by the maintainer. |
| `tv_clean.py` | Scratch duplicate from a null-byte file repair. No content value. |

None of these were ever thesis evidence; several used noncanonical constants.
Numbers from this folder must not be quoted without re-deriving them on the
canonical costs in `docs/FORMAT_CANONICAL.md`.
