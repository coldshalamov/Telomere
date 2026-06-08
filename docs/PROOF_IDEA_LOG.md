# Telomere Proof Idea Log

This log records the innovation loop for the proof-kernel sweep. Ideas are kept
only when they remain Telomere-native: deterministic exact regeneration by seed,
self-delimiting decode, literal fallback, and no uncharged external help.

| # | idea | disposition | note |
| ---: | --- | --- | --- |
| 1 | `strict_baseline` | implemented | Canonical strict seed replacement only. |
| 2 | `left_to_right_selector` | implemented | Deterministic disjoint-window lower selector. |
| 3 | `greedy_largest_gain_selector` | implemented | Deterministic middle selector with overlap loss. |
| 4 | `oracle_weighted_interval_bound` | bounded | Upper bound that credits all positive windows before conflicts. |
| 5 | `equal_size_neutral_refresh` | implemented | Zero-growth legal records refresh current-layer bits. |
| 6 | `retained_bloat_delta_1` | implemented | Encoder-only retained variants within one bit of the main path. |
| 7 | `retained_bloat_delta_8` | implemented | Encoder-only retained variants within eight bits of the main path. |
| 8 | `retained_bloat_delta_64` | implemented | Wide retained-variant upper stress test. |
| 9 | `max_variants_2` | implemented | Two live variants per position. |
| 10 | `max_variants_4` | implemented | Four live variants per position. |
| 11 | `max_variants_16` | implemented | Sixteen live variants per position. |
| 12 | `superposed_bundle_search` | implemented | Arity windows multiply retained variants across positions. |
| 13 | `whole_window_retained_bundles` | implemented | Retained equal/bloat arity-window records add non-decomposed lower-layer alternatives. |
| 14 | `pass_depth_16` | implemented | Small seed-depth schedule point. |
| 15 | `pass_depth_64` | implemented | Mid seed-depth schedule point. |
| 16 | `pass_depth_160` | implemented | Wide conceptual seed-depth schedule point. |
| 17 | `two_phase_depth_schedule` | implemented | Profile-known first-pass depth and later-pass depth schedule. |
| 18 | `byte_aligned_literal_initialization` | implemented | Charges the exact 3+5 literal overhead for byte-aligned literal runs. |
| 19 | `block_bits_8` | expanded | One-byte current-entry schedule point beyond the required 2/3/4-byte sweep. |
| 20 | `fixed_bitstream_rechunk_4` | implemented | Profile-known 4-bit chunks after each emitted layer. |
| 21 | `block_bits_16` | implemented | Small current-entry schedule point. |
| 22 | `block_bits_64` | implemented | Larger current-entry schedule point. |
| 23 | `deterministic_rechunk` | implemented | Profile-known bitstream rechunk refresh. |
| 24 | `entry_permutation_profile` | bounded | Charged deterministic permutation profile. |
| 25 | `layer_descriptor_refresh` | implemented | Charged layer descriptor refresh. |
| 26 | `phase_rotated_rechunk` | implemented | Charged deterministic phase rotation. |
| 27 | `multi_profile_selector` | bounded | Allowed only with charged selector bits; bounded as profile metadata. |
| 28 | `future_diversity_selector` | bounded | Upper-bounded by oracle selection with superposition score. |
| 29 | `final_collapse_stage` | implemented | Encoder-state variants collapse to one serialized path. |
| 30 | `external_helper_table` | rejected | Rejected because it violates the fixed-decoder-or-fully-charged rule. |
| 31 | `foreign_frequency_coder` | rejected | Rejected because it replaces seed-addressed exact regeneration. |
