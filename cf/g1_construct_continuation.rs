// expect: private
// G1 (non-fullness): constructing a priced continuation directly (minting
// a morphism the schedule never declared) must FAIL TO COMPILE.
fn main() {
    let _c = evilswarm::price::Continuation { tag: 9, src: 0, dst: 0, w: 0, a: 0, r: 0 };
}
