//! The swarm spine.
//!
//! The public surface is the buyer-facing category: request records with
//! declared fields, declared services, priced continuations exposed as data.
//! Internal regions have no public names (non-fullness is a visibility
//! decision). The invariants are carried by the type system wherever Rust
//! can express them, and by explicit fences everywhere else:
//!
//! - conservation = linearity: a move consumes its input; use-after-move is
//!   a type error; move tokens are not `Clone` (conservation as absence);
//!   dropping a token without booking is denied by the token's `#[must_use]`
//!   contract under the build policy (see the KT-TYP1 receipt for the honest
//!   affine-type audit);
//! - representation is not capability: fragment bytes are readable only
//!   through a read capability;
//! - lifecycle = typestate: declared -> in-flight -> settled / refused;
//!   illegal transitions are unrepresentable;
//! - topology = licensed execution: no payload-to-address function exists
//!   at the type boundary (the request record has no route field);
//! - two representation homes: transfers are priced moves, booked prices are
//!   representation-independent, and bytewise preservation is a declared
//!   interface property, machine-checked by round-trip.

pub mod books;
pub mod fragment;
pub mod homes;
pub mod interface;
pub mod ledger;
pub mod moves;
pub mod price;
pub mod referee;
pub mod sha;

mod internal;
