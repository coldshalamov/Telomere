//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! GpuSeedMatcher is provided by a deterministic CPU implementation.
//!
//! The `gpu` feature is research-only in `.tlmr` v1. It is kept buildable, but
//! it does not enable a trusted production OpenCL path.

// When the `gpu` feature is enabled the research backend in `gpu_impl.rs` is
// used. Otherwise the same public API is provided by `gpu_cpu.rs`.
#[cfg(feature = "gpu")]
#[path = "gpu_impl.rs"]
mod gpu_backend;
#[cfg(not(feature = "gpu"))]
#[path = "gpu_cpu.rs"]
mod gpu_backend;

pub use gpu_backend::GpuSeedMatcher;
