//! Bloom filter support removed in the MVP.
//!
//! Earlier versions used a simple Bloom filter to quickly discard seeds
//! unlikely to match.  The current approach brute-forces matches without
//! this optimization.

// TODO: reinstate Bloom filters once performance profiling warrants it.
