//! Internal region bookkeeping.
//!
//! Deliberately NOT exported (see lib.rs): `internal` is a private module.
//! Non-fullness is a visibility decision — internal regions have no public
//! names, and a buyer-side program that names one does not compile.

/// An internal region identifier. Unconstructible and unnameable from
/// outside the crate.
pub struct RegionId(u32);

impl RegionId {
    pub(crate) fn new(i: u32) -> Self {
        RegionId(i)
    }
}
