//! Move tokens with a typestate lifecycle.
//!
//! declared -> in-flight -> settled / refused. Illegal transitions are
//! unrepresentable: `launch` exists only on `Declared`, `settle`/`refuse`
//! only on `InFlight`. The stage types are sealed (no public constructors).
//!
//! Conservation = linearity, as far as Rust's affine type system carries it:
//! - a move consumes its input: use-after-move is a hard type error;
//! - move tokens are NOT `Clone` (copying a move would mint one);
//! - drop-without-book is denied by `#[must_use]` under the build policy
//!   (see the KT-TYP1 receipt for the honest affine audit and the named
//!   unsafe-adjacent escape hatches, which are out of the safe surface).

use core::marker::PhantomData;

use crate::books::Books;

/// Stage: declared, not yet in flight.
pub struct Declared(());
/// Stage: in flight.
pub struct InFlight(());
/// Stage: settled.
pub struct Settled(());
/// Stage: refused.
pub struct Refused(());

/// A move token in lifecycle stage `S`.
///
/// `#[must_use]`: a token that is dropped without booking leaves an unbooked
/// move; the build policy denies the `unused_must_use` lint.
#[must_use = "a move token must be booked: dropping a token leaves an unbooked move"]
pub struct MoveToken<S> {
    id: u64,
    fee: u64,
    kind: &'static str,
    _stage: PhantomData<S>,
}

impl<S> MoveToken<S> {
    pub fn id(&self) -> u64 {
        self.id
    }

    pub fn fee(&self) -> u64 {
        self.fee
    }

    pub fn kind(&self) -> &'static str {
        self.kind
    }

    fn restage<T>(self) -> MoveToken<T> {
        MoveToken {
            id: self.id,
            fee: self.fee,
            kind: self.kind,
            _stage: PhantomData,
        }
    }
}

impl MoveToken<Declared> {
    /// Constructs a declared token. Crate-private: tokens enter the world
    /// only through the interface (`interface::declare`).
    pub(crate) fn new(id: u64, fee: u64, kind: &'static str) -> Self {
        MoveToken { id, fee, kind, _stage: PhantomData }
    }

    /// declared -> in-flight.
    pub fn launch(self) -> MoveToken<InFlight> {
        self.restage()
    }
}

impl MoveToken<InFlight> {
    /// in-flight -> settled.
    pub fn settle(self) -> MoveToken<Settled> {
        self.restage()
    }

    /// in-flight -> refused.
    pub fn refuse(self) -> MoveToken<Refused> {
        self.restage()
    }
}

impl MoveToken<Settled> {
    /// Book a settled move: posts its fee and consumes the token.
    /// This is the only exit that leaves no unbooked move behind.
    pub fn book(self, books: &mut Books, debit: crate::books::Account, credit: crate::books::Account) {
        let fee = self.fee;
        let _ = books.post(debit, credit, fee as u128);
    }
}

impl MoveToken<Refused> {
    /// Book a refused move (the refund post) and consume the token.
    pub fn book(self, books: &mut Books, debit: crate::books::Account, credit: crate::books::Account) {
        let fee = self.fee;
        let _ = books.post(debit, credit, fee as u128);
    }
}
