//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! GpuSeedMatcher is provided by either a CPU fallback or a GPU-aware
//! implementation depending on the `gpu` feature flag.

// When the `gpu` feature is enabled we compile the stub implementation in
// `gpu_impl.rs`. Otherwise we fall back to a pure CPU simulation contained in
// `gpu_cpu.rs`.
#[cfg(feature = "gpu")]
#[path = "gpu_impl.rs"]
mod gpu_backend;
#[cfg(not(feature = "gpu"))]
#[path = "gpu_cpu.rs"]
mod gpu_backend;

pub use gpu_backend::GpuSeedMatcher;
