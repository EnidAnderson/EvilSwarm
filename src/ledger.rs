//! Hash-chained append-only ledger.
//!
//! Every entry carries the previous entry's hash; the chain verifies
//! end-to-end; tampering with any payload breaks verification.

use crate::sha::sha256;

/// An append-only, hash-chained ledger entry.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LedgerEntry {
    pub payload: Vec<u8>,
    pub prev: [u8; 32],
    pub hash: [u8; 32],
}

/// The genesis previous-hash: all zeros.
pub const GENESIS: [u8; 32] = [0u8; 32];

/// A hash-chained append-only ledger.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Ledger {
    entries: Vec<LedgerEntry>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Tampered {
    pub index: usize,
}

impl Ledger {
    pub fn new() -> Self {
        Ledger { entries: Vec::new() }
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    pub fn head(&self) -> [u8; 32] {
        self.entries.last().map(|e| e.hash).unwrap_or(GENESIS)
    }

    /// Append a payload; returns the entry hash.
    pub fn append(&mut self, payload: &[u8]) -> [u8; 32] {
        let prev = self.head();
        let mut input = Vec::with_capacity(32 + payload.len() + 1);
        input.extend_from_slice(&prev);
        input.push((self.entries.len() as u8).wrapping_add(0));
        input.extend_from_slice(payload);
        let hash = sha256(&input);
        self.entries.push(LedgerEntry {
            payload: payload.to_vec(),
            prev,
            hash,
        });
        hash
    }

    /// Verify the whole chain: linkage and hashes. Returns the index of the
    /// first tampered entry, if any.
    pub fn verify(&self) -> Result<(), Tampered> {
        let mut prev = GENESIS;
        for (i, e) in self.entries.iter().enumerate() {
            if e.prev != prev {
                return Err(Tampered { index: i });
            }
            let mut input = Vec::with_capacity(32 + e.payload.len() + 1);
            input.extend_from_slice(&e.prev);
            input.push((i as u8).wrapping_add(0));
            input.extend_from_slice(&e.payload);
            if sha256(&input) != e.hash {
                return Err(Tampered { index: i });
            }
            prev = e.hash;
        }
        Ok(())
    }

    /// Read-only access (the ledger is append-only through the API).
    pub fn entries(&self) -> &[LedgerEntry] {
        &self.entries
    }

    /// Returns a copy with one payload byte flipped — a verification-demonstration
    /// helper. The original ledger is untouched (append-only through the API).
    pub fn tampered_copy(&self, index: usize, byte: usize) -> Ledger {
        let mut copy = self.clone();
        if let Some(e) = copy.entries.get_mut(index) {
            if byte < e.payload.len() {
                e.payload[byte] ^= 1;
            }
        }
        copy
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn chain_verifies_and_detects_tampering() {
        let mut l = Ledger::new();
        l.append(b"first");
        l.append(b"second");
        l.append(b"third");
        assert_eq!(l.len(), 3);
        assert!(l.verify().is_ok());

        // Tamper with the middle payload: verification must fail there.
        let broken = l.tampered_copy(1, 0);
        assert_eq!(broken.verify(), Err(Tampered { index: 1 }));
    }
}
