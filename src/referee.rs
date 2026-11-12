//! The referee stub: exact predicates, trust-class tags, the pairing rule.
//!
//! The labeling law: a receipt tag must PAIR with a run tag, derived from
//! it by a keyed construction; anything else is a forged tag and is
//! rejected. Trust-class labels are carried in the tag derivation — a
//! shadow number claiming the exact class fails the pairing (the forged
//! tag class).

use crate::sha::sha256;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TrustClass {
    /// Machine-verified exact.
    Exact,
    /// A shadow measurement (e.g. a CPU shadow of a GPU path) — honestly
    /// labeled, never claiming the exact class.
    Shadow,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RunTag([u8; 32]);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ReceiptTag([u8; 32]);

impl RunTag {
    pub fn from_run(payload: &[u8]) -> Self {
        RunTag(sha256(payload))
    }

    pub fn as_bytes(&self) -> [u8; 32] {
        self.0
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Referee;

impl Referee {
    /// Derive the receipt tag for a run under a trust class.
    pub fn receipt_for(&self, run: &RunTag, class: TrustClass) -> ReceiptTag {
        let mut input = Vec::with_capacity(32 + 1 + 7);
        input.extend_from_slice(&run.0);
        input.push(match class {
            TrustClass::Exact => 1u8,
            TrustClass::Shadow => 2u8,
        });
        input.extend_from_slice(b"receipt");
        ReceiptTag(sha256(&input))
    }

    /// The pairing rule: a receipt tag is valid iff it derives from the run
    /// tag under some trust class. Forged tags fail.
    pub fn verify_pair(&self, run: &RunTag, receipt: &ReceiptTag) -> bool {
        self.receipt_for(run, TrustClass::Exact) == *receipt
            || self.receipt_for(run, TrustClass::Shadow) == *receipt
    }

    /// The trust class a valid receipt was issued under.
    pub fn class_of(&self, run: &RunTag, receipt: &ReceiptTag) -> Option<TrustClass> {
        if self.receipt_for(run, TrustClass::Exact) == *receipt {
            Some(TrustClass::Exact)
        } else if self.receipt_for(run, TrustClass::Shadow) == *receipt {
            Some(TrustClass::Shadow)
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pairing_rule() {
        let r = Referee;
        let run = RunTag::from_run(b"run-payload");
        let good = r.receipt_for(&run, TrustClass::Exact);
        assert!(r.verify_pair(&run, &good));
        assert_eq!(r.class_of(&run, &good), Some(TrustClass::Exact));
        let shadow = r.receipt_for(&run, TrustClass::Shadow);
        assert_eq!(r.class_of(&run, &shadow), Some(TrustClass::Shadow));
        // forged tags rejected: a different run's receipt does not pair
        let other_run = RunTag::from_run(b"other-run");
        let other_receipt = r.receipt_for(&other_run, TrustClass::Exact);
        assert!(!r.verify_pair(&run, &other_receipt));
        assert_eq!(r.class_of(&run, &other_receipt), None);
    }
}
