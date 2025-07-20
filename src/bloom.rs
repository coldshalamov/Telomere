//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! Earlier versions used a simple Bloom filter to quickly discard seeds
//! unlikely to match.  The current approach brute-forces matches without
//! this optimization.

// TODO: reinstate Bloom filters once performance profiling warrants it.
