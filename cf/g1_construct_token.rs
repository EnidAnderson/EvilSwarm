// expect: private
// G1 (non-fullness): constructing a move token directly (bypassing the
// interface) must FAIL TO COMPILE.
fn main() {
    let _t = evilswarm::moves::MoveToken::new(1, 10, "serve");
}
