// expect: argument
// G3 (representation is not capability): reading a fragment without a read
// capability must FAIL TO COMPILE.
use evilswarm::fragment::Fragment;

fn main() {
    let f = Fragment::new(b"bytes");
    let _b = f.read();
}
