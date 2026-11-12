//! The buyer-facing interface: declared-field request records and the
//! declaration of moves.
//!
//! The request record has exactly the declared fields — there is no route
//! field, and no payload-to-address function exists at this boundary:
//! topology is licensed execution, never inferred from content. Requests
//! construct valid (parse, don't validate): illegal requests are
//! unrepresentable, not runtime-rejected.

use crate::moves::{Declared, MoveToken};
use crate::price::{continuations_from, valid_service, CONTINUATIONS};
use crate::sha::sha256;

/// The declared verbs (a subset of the filed taxonomy).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Verb {
    Serve,
    Settle,
    Compose,
    Contribute,
}

/// The declared work-component fee for serving from the settled tier
/// (the agreement debt is zero there: paid once, conserved).
pub const SERVE_W: u64 = 10;

/// A validated request record. Fields are private; the constructors are the
/// only way in, and they validate.
pub struct Request {
    verb: Verb,
    service: u8,
    fee: u64,
    payload_digest: [u8; 32],
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct InvalidRequest;

impl Request {
    /// SERVE: work only (served from the settled tier).
    pub fn serve(service: u8, payload: &[u8]) -> Result<Request, InvalidRequest> {
        if !valid_service(service) {
            return Err(InvalidRequest);
        }
        Ok(Request {
            verb: Verb::Serve,
            service,
            fee: SERVE_W,
            payload_digest: sha256(payload),
        })
    }

    /// SETTLE: work + the agreement debt (reconciliation work over the
    /// region: declared number of disagreeing agents at a declared rate).
    pub fn settle(service: u8, agents: u32, rate: u64) -> Result<Request, InvalidRequest> {
        if !valid_service(service) || agents == 0 || agents > 64 || rate == 0 || rate > 100 {
            return Err(InvalidRequest);
        }
        Ok(Request {
            verb: Verb::Settle,
            service,
            fee: SERVE_W + agents as u64 * rate,
            payload_digest: [0u8; 32],
        })
    }

    /// COMPOSE: the fee of the declared continuation between two services.
    /// An undeclared continuation is unrepresentable (Err), not priced.
    pub fn compose(from: u8, to: u8) -> Result<Request, InvalidRequest> {
        if !valid_service(from) || !valid_service(to) {
            return Err(InvalidRequest);
        }
        match CONTINUATIONS.iter().find(|c| c.src == from && c.dst == to) {
            Some(c) => Ok(Request {
                verb: Verb::Compose,
                service: from,
                fee: c.fee(),
                payload_digest: [0u8; 32],
            }),
            None => Err(InvalidRequest),
        }
    }

    pub fn verb(&self) -> Verb {
        self.verb
    }

    pub fn service(&self) -> u8 {
        self.service
    }

    pub fn fee(&self) -> u64 {
        self.fee
    }

    pub fn payload_digest(&self) -> [u8; 32] {
        self.payload_digest
    }
}

/// Declare a move: the only way a move token enters the world.
pub fn declare(id: u64, req: Request) -> MoveToken<Declared> {
    MoveToken::new(id, req.fee, match req.verb {
        Verb::Serve => "serve",
        Verb::Settle => "settle",
        Verb::Compose => "compose",
        Verb::Contribute => "contribute",
    })
}

/// The declared continuations out of a service, as data (the buyer sees
/// the priced morphisms; they cannot construct new ones — the schedule is
/// declared data with private fields).
pub fn continuation_options(service: u8) -> Vec<(u8, u8, u64)> {
    continuations_from(service)
        .iter()
        .map(|c| (c.src(), c.dst(), c.fee()))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn requests_validate_at_construction() {
        assert!(Request::serve(0, b"payload").is_ok());
        assert!(Request::serve(4, b"payload").is_err()); // undeclared service
        assert!(Request::settle(1, 3, 3).is_ok());
        assert_eq!(Request::settle(1, 3, 3).unwrap().fee(), 10 + 9);
        assert!(Request::settle(1, 0, 3).is_err()); // zero agents
        assert!(Request::compose(0, 1).is_ok());
        assert!(Request::compose(3, 1).is_err()); // undeclared continuation
        // every declared continuation is composable through the interface
        for (s, d, f) in continuation_options(0) {
            assert!(Request::compose(s, d).is_ok());
            assert_eq!(Request::compose(s, d).unwrap().fee(), f);
        }
    }
}
