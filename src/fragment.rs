//! Fragments with capability-gated reads: representation is not capability.
//!
//! Holding a fragment (even its full byte set, in whatever representation)
//! is not permission to read it — reads go through `read(&ReadCap)`, and
//! read capabilities are granted by the holder (`grant_read`), never
//! constructed out of thin air (no public constructor on `ReadCap`).
//! A cap is bound to one fragment's digest: it does not open others.

use crate::sha::sha256;

/// A read capability, bound to one fragment. Unforgeable: no public
/// constructor; obtainable only from the fragment's holder.
#[derive(Clone, Debug)]
pub struct ReadCap {
    for_digest: [u8; 32],
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ReadRefused;

/// A content-addressed byte fragment. `Clone` on purpose: fragments are
/// data, not move tokens — copying bytes is not minting a move (moves are
/// the typed tokens; see the `moves` module).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Fragment {
    id: [u8; 32],
    bytes: Vec<u8>,
}

impl Fragment {
    pub fn new(payload: &[u8]) -> Self {
        Fragment { id: sha256(payload), bytes: payload.to_vec() }
    }

    /// The content digest — representation-visible metadata, readable by all.
    pub fn digest(&self) -> [u8; 32] {
        self.id
    }

    pub fn len(&self) -> usize {
        self.bytes.len()
    }

    pub fn is_empty(&self) -> bool {
        self.bytes.is_empty()
    }

    /// The holder of a fragment grants read on it (capability delegation).
    pub fn grant_read(&self) -> ReadCap {
        ReadCap { for_digest: self.id }
    }

    /// Capability-gated read. A cap bound to a different fragment is
    /// refused (representation — or even ownership — is not capability).
    pub fn read<'a>(&'a self, cap: &'a ReadCap) -> Result<&'a [u8], ReadRefused> {
        if cap.for_digest == self.id {
            Ok(&self.bytes)
        } else {
            Err(ReadRefused)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn capability_discipline() {
        let f = Fragment::new(b"secret bytes");
        let g = Fragment::new(b"other bytes");
        let cap = f.grant_read();
        assert_eq!(f.read(&cap), Ok(&b"secret bytes"[..]));
        // the cap does not open a different fragment
        assert_eq!(g.read(&cap), Err(ReadRefused));
    }
}
