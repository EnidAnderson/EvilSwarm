// expect: must be used
// G2 (linearity): a move token dropped without booking must FAIL TO
// COMPILE (the token's must-use contract, denied by the build policy).
use evilswarm::interface::Request;

fn main() {
    let req = Request::serve(0, b"p").unwrap();
    evilswarm::interface::declare(0, req);
}
