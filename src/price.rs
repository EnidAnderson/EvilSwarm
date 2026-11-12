//! The filed fee schedule (as data): four declared services, eight priced
//! continuations, the price law fee = W + A + R, and path enumeration over
//! the declared continuations (identity is free; composition sums fees).

pub type ServiceId = u8;

pub const SERVICES: usize = 4;

/// A priced continuation as declared data: source, destination, and the
/// three price-law components (work, agreement debt, composition residue).
/// The fields are crate-private: buyers READ the declared schedule (via
/// the accessors); they cannot construct continuations — the schedule is
/// declared, not user-minted.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Continuation {
    pub(crate) tag: u8,
    pub(crate) src: ServiceId,
    pub(crate) dst: ServiceId,
    pub(crate) w: u64,
    pub(crate) a: u64,
    pub(crate) r: u64,
}

impl Continuation {
    pub fn tag(&self) -> u8 {
        self.tag
    }

    pub fn src(&self) -> ServiceId {
        self.src
    }

    pub fn dst(&self) -> ServiceId {
        self.dst
    }

    pub fn w(&self) -> u64 {
        self.w
    }

    pub fn a(&self) -> u64 {
        self.a
    }

    pub fn r(&self) -> u64 {
        self.r
    }

    pub fn fee(&self) -> u64 {
        self.w + self.a + self.r
    }
}

/// The declared continuation schedule (as filed with the service algebra).
pub const CONTINUATIONS: [Continuation; 8] = [
    Continuation { tag: 0, src: 0, dst: 1, w: 30, a: 500, r: 12 },
    Continuation { tag: 1, src: 1, dst: 2, w: 20, a: 400, r: 15 },
    Continuation { tag: 2, src: 2, dst: 3, w: 25, a: 350, r: 10 },
    Continuation { tag: 3, src: 0, dst: 2, w: 45, a: 800, r: 25 },
    Continuation { tag: 4, src: 1, dst: 3, w: 40, a: 700, r: 22 },
    Continuation { tag: 5, src: 3, dst: 0, w: 35, a: 600, r: 18 },
    Continuation { tag: 6, src: 2, dst: 0, w: 30, a: 550, r: 16 },
    Continuation { tag: 7, src: 0, dst: 3, w: 50, a: 900, r: 30 },
];

/// The transfer fee (W component) for a representation-home transfer.
pub const TRANSFER_W: u64 = 10;

pub fn valid_service(s: ServiceId) -> bool {
    s < SERVICES as u8
}

/// The declared continuations out of a service, as data.
pub fn continuations_from(s: ServiceId) -> Vec<Continuation> {
    CONTINUATIONS.iter().copied().filter(|c| c.src == s).collect()
}

/// A declared path from a starting service through a sequence of declared
/// continuations (possibly empty = the identity at that service).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Path {
    pub start: ServiceId,
    pub steps: Vec<Continuation>,
}

impl Path {
    pub fn identity(s: ServiceId) -> Self {
        Path { start: s, steps: Vec::new() }
    }

    pub fn src(&self) -> ServiceId {
        self.start
    }

    pub fn dst(&self) -> ServiceId {
        self.steps.last().map(|c| c.dst).unwrap_or(self.start)
    }

    pub fn composable(&self) -> bool {
        for w in self.steps.windows(2) {
            if w[0].dst != w[1].src {
                return false;
            }
        }
        true
    }

    /// Composition sums fees; identity is free.
    pub fn fee(&self) -> u64 {
        self.steps.iter().map(|c| c.fee()).sum()
    }

    pub fn extend(&self, c: Continuation) -> Option<Path> {
        if self.dst() != c.src {
            return None;
        }
        let mut steps = self.steps.clone();
        steps.push(c);
        Some(Path { start: self.start, steps })
    }
}

/// All declared paths of length at most 2 (identities included), over the
/// declared continuation schedule: 4 identities + 8 one-step + 15 two-step.
pub fn paths_up_to_len2() -> Vec<Path> {
    let mut out = Vec::new();
    for s in 0..SERVICES {
        out.push(Path::identity(s as ServiceId));
    }
    for c in CONTINUATIONS.iter() {
        let one = Path::identity(c.src).extend(*c).unwrap();
        out.push(one.clone());
        for d in CONTINUATIONS.iter() {
            if let Some(p) = one.extend(*d) {
                out.push(p);
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn schedule_laws() {
        // fee law: fee = W + A + R on every continuation
        for c in CONTINUATIONS.iter() {
            assert_eq!(c.fee(), c.w + c.a + c.r);
        }
        // 27 declared paths: 4 identities + 8 len-1 + 15 len-2
        let ps = paths_up_to_len2();
        assert_eq!(ps.len(), 27);
        for p in &ps {
            assert!(p.composable());
        }
        // identity is free; composition sums fees
        assert_eq!(Path::identity(0).fee(), 0);
        let p = Path::identity(0)
            .extend(CONTINUATIONS[0])
            .unwrap()
            .extend(CONTINUATIONS[1])
            .unwrap();
        assert_eq!(p.src(), 0);
        assert_eq!(p.dst(), 2);
        assert_eq!(p.fee(), CONTINUATIONS[0].fee() + CONTINUATIONS[1].fee());
        // a non-composable extension is refused (None, not a wrong path)
        assert!(Path::identity(0).extend(CONTINUATIONS[5]).is_none());
    }
}
