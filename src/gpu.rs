#[cfg(feature = "gpu")]
#[path = "gpu_impl.rs"]
mod gpu_impl;
#[cfg(feature = "gpu")]
pub use gpu_impl::GpuSeedMatcher;

#[cfg(not(feature = "gpu"))]
#[path = "gpu_cpu.rs"]
mod gpu_cpu;
#[cfg(not(feature = "gpu"))]
pub use gpu_cpu::GpuSeedMatcher;
