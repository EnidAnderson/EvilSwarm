//! Integration tests (cargo test): the spine's laws at rest.

#[test]
fn books_conservation_under_mixed_workload() {
    use evilswarm::books::Books;
    let mut b = Books::new();
    b.post(0, 1, 100).unwrap();
    b.post(1, 2, 30).unwrap();
    b.post(2, 0, 70).unwrap();
    assert!(b.conservation_holds());
    let bal = b.balances();
    assert_eq!(bal[&0], -30);
    assert_eq!(bal[&1], 70);
    assert_eq!(bal[&2], -40);
}

#[test]
fn typestate_lifecycle_via_interface() {
    use evilswarm::books::Books;
    use evilswarm::interface::{self, Request};
    let req = Request::compose(0, 1).unwrap();
    let mut books = Books::new();
    interface::declare(0, req).launch().settle().book(&mut books, 7, 8);
    assert_eq!(books.len(), 1);
    assert!(books.conservation_holds());
}

#[test]
fn transfer_fees_post_and_round_trip_preserves() {
    use evilswarm::books::Books;
    use evilswarm::fragment::Fragment;
    use evilswarm::homes;
    let mut b = Books::new();
    let cpu = homes::into_cpu_home(Fragment::new(b"abc"));
    let gpu = homes::cpu_to_gpu(&cpu, &mut b);
    let back = homes::gpu_to_cpu(&gpu, &mut b);
    assert_eq!(cpu, back);
    assert_eq!(b.len(), 2);
    assert!(b.conservation_holds());
}
