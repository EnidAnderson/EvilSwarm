//! The KT-TYP1 runtime gates (G4 and the positive checks), run by the
//! harness binary. Compile-fail gates (G1, G2, G3, G6-negative) are driven
//! by the harness script against the cf/ files; this binary prints the
//! deterministic runtime transcript.

use evilswarm::books::{Books, MalformedPost};
use evilswarm::fragment::Fragment;
use evilswarm::homes::{self, CpuFragment};
use evilswarm::interface::{self, Request};
use evilswarm::ledger::Ledger;
use evilswarm::price::{paths_up_to_len2, Path, CONTINUATIONS};
use evilswarm::referee::{Referee, RunTag, TrustClass};
use evilswarm::sha::sha256;

fn hex(b: &[u8; 32]) -> String {
    b.iter().map(|x| format!("{:02x}", x)).collect()
}

fn main() {
    // SHA-256 against public vectors.
    assert_eq!(
        hex(&sha256(b"abc")),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
    assert_eq!(
        hex(&sha256(b"")),
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    );
    assert_eq!(
        hex(&sha256(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq")),
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
    );
    println!("SHA256 public vectors: 3/3 ok");

    // G4 — round-trip: a 512-byte declared byte set, CPU -> GPU -> CPU,
    // bytewise identical (the declared preservation property).
    let payload: Vec<u8> = (0..512u32).map(|i| (i % 251) as u8).collect();
    let frag = Fragment::new(&payload);
    let mut books = Books::new();
    let cpu = homes::into_cpu_home(frag.clone());
    let gpu = homes::cpu_to_gpu(&cpu, &mut books);
    let cpu2 = homes::gpu_to_cpu(&gpu, &mut books);
    assert_eq!(cpu, cpu2);
    assert_eq!(frag.digest(), cpu2.fragment().digest());
    let cap = frag.grant_read();
    assert_eq!(frag.read(&cap), Ok(payload.as_slice()));
    assert_eq!(cpu2.fragment().read(&cap), Ok(payload.as_slice()));
    // transfers posted two W fees (priced moves, never free copies)
    assert_eq!(books.len(), 2);
    println!("G4 round-trip: 512 bytes, cpu->gpu->cpu, bytewise identical; transfers priced: 2 W-fees posted");

    // G4 — price coherence: the same 27-path workload executed in each
    // home posts identical books (representation-independent books).
    let paths = paths_up_to_len2();
    assert_eq!(paths.len(), 27);
    let mut cpu_books = Books::new();
    let mut gpu_books = Books::new();
    let cpu_frag = homes::into_cpu_home(Fragment::new(b"workload"));
    let gpu_frag = homes::into_gpu_home(Fragment::new(b"workload"));
    for p in &paths {
        homes::execute_on_cpu(&cpu_frag, p, &mut cpu_books, 7, 8);
        homes::execute_on_gpu(&gpu_frag, p, &mut gpu_books, 7, 8);
    }
    assert_eq!(cpu_books, gpu_books);
    assert!(cpu_books.conservation_holds());
    println!("G4 price coherence: 27 paths on each home, books identical, conservation holds");

    // G6 positive — books are Clone (the cartesian side of the boundary).
    let cloned = cpu_books.clone();
    assert_eq!(cloned, cpu_books);
    println!("G6 clone-boundary positive: books Clone ok (move tokens carry no Clone - cf/g6)");

    // Ledger — chain, replay determinism, tamper detection.
    let mut l1 = Ledger::new();
    for i in 0..5u8 {
        l1.append(&[i, i, i]);
    }
    assert!(l1.verify().is_ok());
    let mut l2 = Ledger::new();
    for i in 0..5u8 {
        l2.append(&[i, i, i]);
    }
    assert_eq!(l1, l2);
    assert_eq!(l1.head(), l2.head());
    let broken = l1.tampered_copy(2, 0);
    assert!(broken.verify().is_err());
    println!("LEDGER: 5 entries verify, replay deterministic (identical chain), tamper detected");

    // Referee — pairing rule: 500 forged tags rejected, 0 false rejections.
    let r = Referee;
    let run = RunTag::from_run(b"the-run");
    let exact = r.receipt_for(&run, TrustClass::Exact);
    let shadow = r.receipt_for(&run, TrustClass::Shadow);
    assert!(r.verify_pair(&run, &exact));
    assert!(r.verify_pair(&run, &shadow));
    assert_eq!(r.class_of(&run, &exact), Some(TrustClass::Exact));
    assert_eq!(r.class_of(&run, &shadow), Some(TrustClass::Shadow));
    let mut forged_rejected = 0u32;
    for i in 0..500u32 {
        let other = RunTag::from_run(&i.to_be_bytes());
        let other_receipt = r.receipt_for(&other, TrustClass::Exact);
        if !r.verify_pair(&run, &other_receipt) {
            forged_rejected += 1;
        }
    }
    assert_eq!(forged_rejected, 500);
    println!("REFEREE pairing: 2 valid receipts accepted, 500/500 forged tags rejected, 0 false rejections");

    // Price law — fee = W + A + R on every continuation; composition sums;
    // identity free; the declared schedule has 8 continuations over 4 services.
    for c in CONTINUATIONS.iter() {
        assert_eq!(c.fee(), c.w() + c.a() + c.r());
    }
    let p = Path::identity(0)
        .extend(CONTINUATIONS[0])
        .unwrap()
        .extend(CONTINUATIONS[1])
        .unwrap();
    assert_eq!(
        p.fee(),
        CONTINUATIONS[0].fee() + CONTINUATIONS[1].fee()
    );
    assert_eq!(Path::identity(3).fee(), 0);
    println!("PRICE: fee=W+A+R on 8/8 continuations, composition sums, identity free");

    // Lifecycle — the typestate progression through the public interface.
    let req = Request::serve(0, b"payload").unwrap();
    let t = interface::declare(1, req);
    let t = t.launch();
    let t = t.settle();
    let mut lb = Books::new();
    t.book(&mut lb, 7, 8);
    assert_eq!(lb.len(), 1);
    assert!(lb.conservation_holds());

    let req2 = Request::settle(1, 3, 3).unwrap();
    let t2 = interface::declare(2, req2);
    let t2 = t2.launch();
    let t2 = t2.refuse();
    t2.book(&mut lb, 8, 7);
    assert_eq!(lb.len(), 2);
    assert!(lb.conservation_holds());
    println!("LIFECYCLE: declare->launch->settle->book and declare->launch->refuse->book ok, books balanced");

    // Malformed posts refused (zero amount, self-post).
    let mut mb = Books::new();
    assert_eq!(mb.post(1, 2, 0), Err(MalformedPost));
    assert_eq!(mb.post(1, 1, 5), Err(MalformedPost));
    assert_eq!(mb.len(), 0);
    println!("FENCES: malformed posts refused, zero posts, books unchanged");

    println!("KT-TYP1 RUNTIME GATES GREEN");
}
