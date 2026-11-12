// expect: private
// G1 (non-fullness): a buyer-side program must not be able to name an
// internal region. This file must FAIL TO COMPILE.
use evilswarm::internal::RegionId;

fn main() {
    let _ = RegionId::new(1);
}
