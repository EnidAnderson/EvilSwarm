//! Two representation homes for fragments.
//!
//! A transfer between homes is a priced move (a W fee posts to the books —
//! never a free copy). The declared interface property: a transfer states
//! what it preserves, and for fragments that property is BYTEWISE
//! preservation, machine-checked by round-trip. Booked prices are
//! representation-independent: the same workload posts the same books
//! whichever home executed it (the homes are where work runs; they are
//! not separate bookkeeping entities — only a TRANSFER is a home-accounted
//! move).
//!
//! Honest scope: in the skeleton the GPU home is the representation-home
//! interface contract (the same logical fragment in the second home); the
//! hardware path, its kernels, and its benchmark pre-registrations belong
//! to the GPU milestone and are NOT claimed here.

use crate::books::{Account, Books};
use crate::fragment::Fragment;
use crate::price::{Path, TRANSFER_W};

/// The bookkeeping accounts for home-to-home transfers (a transfer is a
/// real, priced move; execution is not).
pub const CPU_HOME: Account = 900;
pub const GPU_HOME: Account = 901;

/// A fragment resident in the CPU home.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CpuFragment {
    pub(crate) frag: Fragment,
}

/// A fragment resident in the GPU home.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GpuFragment {
    pub(crate) frag: Fragment,
}

pub fn into_cpu_home(f: Fragment) -> CpuFragment {
    CpuFragment { frag: f }
}

pub fn into_gpu_home(f: Fragment) -> GpuFragment {
    GpuFragment { frag: f }
}

impl CpuFragment {
    /// The resident fragment (reads still go through its capability).
    pub fn fragment(&self) -> &Fragment {
        &self.frag
    }
}

impl GpuFragment {
    /// The resident fragment (reads still go through its capability).
    pub fn fragment(&self) -> &Fragment {
        &self.frag
    }
}

/// CPU -> GPU: a priced transfer (W fee posted), bytewise-preserving.
pub fn cpu_to_gpu(cpu: &CpuFragment, books: &mut Books) -> GpuFragment {
    let _ = books.post(CPU_HOME, GPU_HOME, TRANSFER_W as u128);
    GpuFragment { frag: cpu.frag.clone() }
}

/// GPU -> CPU: a priced transfer (W fee posted), bytewise-preserving.
pub fn gpu_to_cpu(gpu: &GpuFragment, books: &mut Books) -> CpuFragment {
    let _ = books.post(GPU_HOME, CPU_HOME, TRANSFER_W as u128);
    CpuFragment { frag: gpu.frag.clone() }
}

/// Execute a declared path's fee bookkeeping in the CPU home. The posts
/// are home-independent (the coherence law): identical inputs, identical
/// books, whichever home runs the work.
pub fn execute_on_cpu(_cpu: &CpuFragment, path: &Path, books: &mut Books, payer: Account, payee: Account) {
    let _ = books.post(payer, payee, path.fee() as u128);
}

/// Execute a declared path's fee bookkeeping in the GPU home. Byte-for-byte
/// the same posts as `execute_on_cpu`: fees are structure-relative, not
/// home-relative.
pub fn execute_on_gpu(_gpu: &GpuFragment, path: &Path, books: &mut Books, payer: Account, payee: Account) {
    let _ = books.post(payer, payee, path.fee() as u128);
}
