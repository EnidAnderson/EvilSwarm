// expect: `clone`
// G6 (Clone boundary, negative side): move tokens must NOT be Clone —
// copying a move would mint one. This must FAIL TO COMPILE.
use evilswarm::interface::Request;

fn main() {
    let req = Request::serve(0, b"p").unwrap();
    let t = evilswarm::interface::declare(0, req);
    let _t2 = t.clone();
}
