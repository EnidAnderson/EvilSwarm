# EvilSwarm

Decentralized, continuously-learning GPU swarm. This repository carries the public design ledger (issues, labels `invariant` / `research`) and the Rust skeleton crate filed as **IMPL-01 (#89)**.

## What is in the crate (v0.1.0, skeleton)

- `src/sha.rs` — SHA-256, std-only, checked against the public FIPS 180-4 test vectors (empty string, "abc", "abcdbcdecdefdefgefghfghighjhkijijkljklmklmnlmnomnopnopq").
- `src/ledger.rs` — append-only hash-chained ledger: genesis block, chain verification, tamper detection, deterministic replay.
- `src/books.rs` — double-entry books: every post debits one account and credits another by the same amount; conservation (sum of balances = 0) is checked, not assumed.
- `src/price.rs` — the declared fee schedule of #84: 4 services, 8 priced continuations (fee = W + A + R), 27 paths up to length 2. Continuations expose read-only accessors: buyers read the schedule, they cannot write it.
- `src/moves.rs` — typestate move tokens: `Declared -> InFlight -> Settled | Refused`; tokens are not `Clone`; booking consumes the token.
- `src/interface.rs` — the only token constructor (`declare`); requests validated at the boundary (Serve / Settle / Compose / Contribute); undeclared continuations refused.
- `src/fragment.rs` — fragments and read capabilities: `read(&cap)` only, and a cap is bound to one fragment's digest. Representation is not capability.
- `src/homes.rs` — CPU and GPU homes as two representations of one fragment: transfers are priced and bytewise-preserving; execution posts identical books on either home (the coherence contract of #85). The GPU home is an interface contract; hardware belongs to M1.
- `src/referee.rs` — receipt pairing stub: exact-run vs shadow-run classes, forged tags rejected.
- `src/internal.rs` — deliberately private module (an API-surface witness).
- `src/bin/gates.rs` — deterministic runtime-gates transcript.
- `cf/` — compile-fail witnesses: each file must FAIL to compile with the expected diagnostic.
- `tests/` — integration tests.
- `ktyp1.sh` — the KT-TYP1 harness (build + runtime gates + compile-fail loop).

## Honest status (two-track rule)

This crate is on the **MILESTONE track as the skeleton**. No acceptance target M1–M5 (see #64) is claimed: M1/M2 are hardware-gated, and the crate contains no GPU code and no floating-point arithmetic.

The type-contract battery **KT-TYP1** (pre-registered in #85, amended in #86) retired green — receipt **R-TYP1** on #85: 11 runtime gate lines, 7/7 compile-fail witnesses refused with the expected diagnostics, 10/10 tests, two-run replay bitwise identical, transcript sha256 `5a539647c438fda8080e8cbe0561486668b77f6b2b5785ae5623e8d376fe2e86`.

Honest caveat (F-TYP1-0, disclosed in #89 before the run): Rust is affine, not linear. Use-after-move is a hard type error; drop-without-book is enforced by `#[must_use]` plus `--deny unused_must_use` in the harness build policy. Escape hatches (`mem::forget`, `ManuallyDrop`) are outside the safe surface under test, named, not banned.

## Building

```
cargo build
cargo test
sh ktyp1.sh
```

Std-only; no external crates. Validated on rustc 1.99.1, target `x86_64-unknown-linux-musl`, `rust-lld` linker, self-contained linking (the build environment has no system C compiler).

## Next M-track items

- Framed int8 kernels path (M1 pre-registration, hardware-gated).
- Network layer.
