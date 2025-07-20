//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! The original code loaded precomputed decompressed strings and used them
//! to bias seed selection.  Future research may restore this module to
//! support advanced heuristics.

// TODO: reintroduce gloss table support when non‑brute‑force methods are explored.
