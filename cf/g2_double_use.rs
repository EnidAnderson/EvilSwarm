// expect: moved
// G2 (linearity): double-use of a move token must FAIL TO COMPILE.
use evilswarm::interface::Request;

fn main() {
    let req = Request::serve(0, b"p").unwrap();
    let t = evilswarm::interface::declare(0, req);
    let a = t.launch();
    let b = t.launch();
    let _ = (a, b);
}
