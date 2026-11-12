"""The KT-PER4 acceptance battery for the kzperiod library.

Gates G1-G5 run in a single process twice; G6 confirms the two runs are
bitwise identical, scans the seven library modules for out-of-contract
vocabulary, and confirms the transcript itself carries no approximate
values. The printed payload is deterministic: the same inputs must give
the same transcript and the same results hash on every run.
"""

import hashlib
import json
import re
import sys

import kzperiod
import kzperiod.arena
import kzperiod.exact
import kzperiod.godel
import kzperiod.lanes
import kzperiod.moves
import kzperiod.words
from kzperiod.arena import Arena, SIZE_CLASSES, WORD_LIMIT
from kzperiod.exact import LibRefusal, Q
from kzperiod.godel import deserialize, hash128, serial_number, serialize
from kzperiod.lanes import (ACC_LIMIT, LaneStack, QMat, crt_lift, inv_mod,
                            lane_matmul, modulus_product, wang_reconstruct)
from kzperiod.moves import (MoveRecord, Proof, TranspositionTable,
                            weight4_proof, verify_weight4)
from kzperiod.words import (Word, census_rec, compose, compositions,
                            is_room, parse_blocks, room_keys, shuffle_words,
                            stuffle2, word_from_indices)

PRIMES = (1019, 509, 1021)
CENSUS = [1, 1, 1, 2, 2, 3, 4, 5, 7, 9, 12, 16, 21, 28, 37, 49, 65, 86,
          114, 151, 200, 265, 351]


class T:
    """One gate's ledger of checks, refusals, and failures."""

    def __init__(self, name):
        self.name = name
        self.checks = 0
        self.failures = 0
        self.refusals = 0
        self.failed = []

    def check(self, label, cond):
        self.checks += 1
        if not cond:
            self.failures += 1
            self.failed.append(label)

    def refuse(self, label, fn):
        self.checks += 1
        try:
            fn()
        except LibRefusal:
            self.refusals += 1
            return
        self.failures += 1
        self.failed.append(label)

    def gate(self):
        return {"gate": self.name, "checks": self.checks,
                "failures": self.failures, "refusals": self.refusals,
                "failed": self.failed}


def gate_g1():
    t = T("G1 canonical serialization")
    objs = list(range(-50, 450))
    objs += [Q(3 * i + 1, 7 * i + 3) for i in range(200)]
    objs += [Q(1, 2), Q(2, 4), Q(-2, -4)]
    objs += [b"", b"a", b"abc", bytes(range(16)), b"z" * 16]
    objs += [[], [1], [1, [2, [3]]], [[1], 2], [Q(1, 2), [Q(3, 4)]],
             [b"x", [1, [2]]], [Word(2, 1), [Word(3, 1)]]]
    for w in range(1, 11):
        for k in range(1 << w):
            objs.append(Word(w, k))
    for w in (11, 12):
        objs += room_keys(w)
    objs += [MoveRecord(1 + i % 3, (i % 7, i % 11, i)).canonical_list()
             for i in range(30)]
    population = len(objs)
    canon = {}
    for o in objs:
        b = serialize(o)
        t.check("serialize deterministic", b == serialize(o))
        rt = deserialize(b)
        t.check("round trip", rt == o)
        t.check("re-serialize stable", serialize(rt) == b)
        canon[b] = o
    merged = population - len(canon)
    t.check("canonical merging witnessed", merged >= 2)
    serials = sorted(serial_number(o) for o in canon.values())
    t.check("serials distinct", len(set(serials)) == len(serials))
    strict = True
    for i in range(len(serials) - 1):
        if serials[i] >= serials[i + 1]:
            strict = False
    t.check("serial order strict", strict)
    hashes = [hash128(o) for o in canon.values()]
    t.check("hash keys distinct", len(set(hashes)) == len(hashes))
    t.check("equal values one serial",
            serial_number(Q(2, 4)) == serial_number(Q(1, 2))
            == serial_number(Q(-2, -4)))
    t.refuse("boolean refused", lambda: serialize(True))
    t.refuse("zero denominator refused", lambda: Q(1, 0))
    t.refuse("word key beyond weight refused", lambda: Word(3, 8))
    t.refuse("mapping refused", lambda: serialize({}))
    t.refuse("approximate value refused", lambda: serialize(15 / 10))
    t.refuse("boolean word key refused", lambda: Word(3, True))
    g = t.gate()
    g["population"] = population
    g["canonical_forms"] = len(canon)
    g["merged"] = merged
    return g


def gate_g2():
    t = T("G2 arena and aliasing")
    a = Arena()
    hs = [a.alloc(1 + i % 3, [i % 7, i % 5], bytes([i % 256]))
          for i in range(200)]
    t.check("all live after load", a.live_count() == 200)
    t.check("integrity after load", a.integrity())
    freed = hs[0::3]
    for h in freed:
        a.free(h)
    t.check("every third freed", len(freed) == 67)
    t.check("live count after churn", a.live_count() == 133)
    t.check("integrity after churn", a.integrity())
    t.check("live read", a.read(hs[1]) == (2, [1, 1], bytes([1])))
    big = a.alloc(1, [WORD_LIMIT - 1, 0])
    t.check("machine-width word accepted", a.read(big)[1] == [WORD_LIMIT - 1, 0])
    t.check("live count after big word", a.live_count() == 134)
    t.check("size class ladder", SIZE_CLASSES == (1, 2, 4, 8, 16))
    b1 = Arena()
    b1.alloc(1, [5, 6])
    b1.alloc(1, [7])
    b2 = Arena()
    b2.alloc(1, [7])
    b2.alloc(1, [5, 6])
    t.check("snapshot order-insensitive", b1.snapshot() == b2.snapshot())
    b3 = Arena()
    b3.alloc(1, [5, 6])
    h7 = b3.alloc(1, [7])
    b3.free(h7)
    b4 = Arena()
    b4.alloc(1, [5, 6])
    t.check("snapshot after free", b3.snapshot() == b4.snapshot())
    t.check("snapshot not live-equal", b1.snapshot() != b3.snapshot())
    fresh = a.alloc(9, [1])
    t.check("handles never recycled", fresh > max(hs))
    t.refuse("freed handle dead", lambda: a.read(freed[0]))
    t.refuse("double free refused", lambda: a.free(freed[0]))
    t.refuse("unknown handle read", lambda: a.read(999999))
    t.refuse("unknown handle free", lambda: a.free(999999))
    t.refuse("word beyond machine width", lambda: a.alloc(1, [1 << 31]))
    t.refuse("negative word refused", lambda: a.alloc(1, [-1]))
    t.refuse("empty words refused", lambda: a.alloc(1, []))
    t.refuse("payload past ladder", lambda: a.alloc(1, [1], b"x" * 17))
    t.refuse("negative species refused", lambda: a.alloc(-1, [1]))
    t.refuse("boolean species refused", lambda: a.alloc(True, [1]))
    t.refuse("boolean word refused", lambda: a.alloc(1, [True]))
    return t.gate()


def gate_g3():
    t = T("G3 residue stacks and height ledgers")
    m = modulus_product(PRIMES)
    t.check("modulus product tie", m == 529563091)
    xq, yq, x, y, mv = verify_weight4(weight4_proof(), PRIMES)
    t.check("weight4 X value", xq == Q(3, 4))
    t.check("weight4 Y value", yq == Q(1, 4))
    t.check("X lift tie", x == 397172319)
    t.check("Y lift tie", y == 132390773)
    t.check("modulus tie through verifier", mv == m)
    a = QMat.from_qs([[Q(1, 2), Q(1, 3)], [Q(1, 5), Q(1, 6)]])
    b = QMat.from_qs([[Q(1, 7), Q(2, 1)], [Q(3, 1), Q(1, 11)]])
    t.check("A frame tie", (a.nums, a.den) == ([15, 10, 6, 5], 30))
    t.check("B frame tie", (b.nums, b.den) == ([11, 154, 231, 7], 77))
    la = a.to_lanes(PRIMES)
    lb = b.to_lanes(PRIMES)
    t.check("positive control residue", all(lb.residue(i, 1, 0) == 3
                                            for i in range(3)))
    c = lane_matmul(la, lb)
    cnum = [2475, 2380, 1221, 959]
    dc, nc = 2310, 2475
    t.check("uniqueness gate arithmetic",
            2 * nc * dc == 11434500 and 11434500 < m)
    exact = [[Q(15, 14), Q(34, 33)], [Q(37, 70), Q(137, 330)]]
    for i in range(2):
        for j in range(2):
            xij = crt_lift(c.entry_residues(i, j), PRIMES)
            r, s = wang_reconstruct(xij, m, nc, dc)
            t.check("gemm equals exact product", Q(r, s) == exact[i][j])
            t.check("certificate congruence",
                    (exact[i][j].n * dc - cnum[i * 2 + j] * exact[i][j].d)
                    % m == 0)
    lanes2 = [list(lane) for lane in c.lanes]
    lanes2[0][0] = (lanes2[0][0] + 1) % PRIMES[0]
    ct = LaneStack(PRIMES, lanes2, 2, 2)
    xt = crt_lift(ct.entry_residues(0, 0), PRIMES)
    caught = False
    try:
        r, s = wang_reconstruct(xt, m, nc, dc)
        caught = Q(r, s) != exact[0][0]
    except LibRefusal:
        caught = True
    t.check("lane tamper caught", caught)
    t.check("zero reconstructs", wang_reconstruct(0, m, 5, 4) == (0, 1))
    t.refuse("uniqueness gate refusal", lambda: wang_reconstruct(12, 15, 3, 4))
    t.refuse("ledger box too small", lambda: wang_reconstruct(x, m, 2, 4))
    t.refuse("residue outside range", lambda: wang_reconstruct(m, m, 3, 4))
    t.refuse("lane prime divides denominator", lambda: a.to_lanes((2, 3)))
    t.refuse("lane primes not distinct", lambda: a.to_lanes((5, 5)))
    t.refuse("lane order mismatch",
             lambda: lane_matmul(la, b.to_lanes((1021, 509, 1019))))
    t.refuse("non-invertible residue", lambda: inv_mod(2, 4))
    t.refuse("non-coprime lift", lambda: crt_lift([0, 0], (4, 4)))
    pbig = 2147483647
    f2 = QMat(2, 2, [1] * 4, 1).to_lanes((pbig,))
    c2 = lane_matmul(f2, f2)
    t.check("fence passes at inner dimension 2", c2.residue(0, 0, 0) == 2)
    f3 = QMat(3, 3, [1] * 9, 1).to_lanes((pbig,))
    t.refuse("fence refuses at inner dimension 3",
             lambda: lane_matmul(f3, f3))
    fence2 = 2 * (pbig - 1) * (pbig - 1)
    fence3 = 3 * (pbig - 1) * (pbig - 1)
    t.check("fence boundary arithmetic", fence2 < ACC_LIMIT <= fence3)
    return t.gate()


def gate_g4():
    t = T("G4 iterated words and the two clocks")
    t.check("clock trace 01001", parse_blocks(Word(5, int("01001", 2))) == [2, 3])
    t.check("clock trace 00101", parse_blocks(Word(5, int("00101", 2))) == [3, 2])
    census = []
    for w in range(2, 25):
        comps = list(compositions(w))
        census.append(len(comps))
        t.check("census recurrence at %d" % w, len(comps) == census_rec(w))
        for comp in comps:
            wp = compose(comp)
            t.check("compose parse round trip",
                    parse_blocks(wp) == list(comp))
            t.check("room shape", wp.key % 2 == 1 and wp.key < (1 << (w - 1)))
    t.check("census array tie", census == CENSUS)
    t.check("census total tie", sum(census) == 1430)
    candidates = 0
    rooms_found = 0
    for w in range(2, 19):
        gen = sorted(wp.key for wp in room_keys(w))
        brute = []
        for k in range(1, 1 << (w - 1), 2):
            candidates += 1
            if is_room(k, w):
                brute.append(k)
        t.check("brute bijection at %d" % w, brute == gen)
        rooms_found += len(gen)
    t.check("candidate total tie", candidates == 131071)
    t.check("rooms through weight 18", rooms_found == sum(CENSUS[:17]))
    t.check("shuffle of the two clocks",
            shuffle_words(compose([2]), compose([2])) == [(3, 4), (5, 2)])
    t.check("stuffle of the two clocks",
            stuffle2(2, 2) == [(2, 2), (2, 2), (4,)])
    t.check("index word keys",
            (word_from_indices((2, 2)).key, word_from_indices((3, 1)).key,
             word_from_indices((4,)).key) == (5, 3, 1))
    t.check("unit outside the rooms", not is_room(1, 4))
    t.refuse("leading run of three", lambda: parse_blocks(Word(4, 1)))
    t.refuse("head run of zero", lambda: parse_blocks(Word(4, 9)))
    t.refuse("even word refused", lambda: parse_blocks(Word(4, 6)))
    t.refuse("even word refused again", lambda: parse_blocks(Word(3, 2)))
    t.refuse("first index below two", lambda: word_from_indices((1, 2)))
    t.refuse("block outside grammar", lambda: compose([4]))
    t.refuse("weight below one", lambda: Word(0, 0))
    t.refuse("key beyond weight", lambda: Word(2, 4))
    return t.gate()


def gate_g5():
    t = T("G5 proofs and transposition")
    p1 = weight4_proof()
    p2 = weight4_proof()
    t.check("proof id deterministic", p1.proof_id() == p2.proof_id())
    xq, yq, x, y, m = verify_weight4(p1)
    t.check("proof verifies", xq == Q(3, 4) and yq == Q(1, 4))
    t.check("proof values tied", (x, y, m) == (397172319, 132390773, 529563091))

    def tamper(idx, where, val):
        recs = list(p1.records)
        r = recs[idx]
        data = list(r.data)
        data[where] = val
        recs[idx] = MoveRecord(r.kind, data)
        return Proof(recs)

    t.refuse("relation coefficient tamper",
             lambda: verify_weight4(tamper(1, 2, 3)))
    t.refuse("relation rhs tamper", lambda: verify_weight4(tamper(0, 5, 3)))
    t.refuse("certificate tamper", lambda: verify_weight4(tamper(2, 2, 4)))
    t.refuse("claim tamper", lambda: verify_weight4(tamper(4, 2, 5)))
    tt = TranspositionTable()
    recs = [MoveRecord(1 + i % 3, (i % 13, i % 17, i % 19, i))
            for i in range(1000)]
    put_ok = True
    for i, r in enumerate(recs):
        if tt.put(r, i) is not True:
            put_ok = False
    t.check("all puts new", put_ok)
    t.check("zero collisions under full key", tt.collisions == 0)
    get_ok = True
    for i, r in enumerate(recs):
        if tt.get(r) != i:
            get_ok = False
    t.check("all retrievable under full key", get_ok)
    weak = TranspositionTable(lambda cl: hash128(cl) & 255)
    recs3 = recs[:300]
    for r in recs3:
        weak.put(r, 0)
    t.check("weak key collides", weak.collisions > 0)
    weak_ok = True
    for r in recs3:
        if weak.get(r) is None:
            weak_ok = False
    t.check("weak key still exact", weak_ok)
    t.check("duplicate put returns false", weak.put(recs3[0], 1) is False)
    t.check("canonical id deterministic",
            MoveRecord(1, (4,)).canonical_id() == MoveRecord(1, (4,)).canonical_id())
    t.check("canonical id separates",
            MoveRecord(1, (4,)).canonical_id() != MoveRecord(1, (5,)).canonical_id())
    t.refuse("species outside census", lambda: MoveRecord(9, (1,)))
    t.refuse("boolean datum refused", lambda: MoveRecord(1, (True,)))
    t.refuse("empty proof refused", lambda: Proof([]))
    return t.gate()


def _no_approx(x):
    if isinstance(x, bool) or isinstance(x, int) or isinstance(x, str):
        return True
    if isinstance(x, float):
        return False
    if isinstance(x, list):
        return all(_no_approx(v) for v in x)
    if isinstance(x, dict):
        return all(_no_approx(k) and _no_approx(v) for k, v in x.items())
    return False


def gate_g6(core1, core2):
    t = T("G6 two-run replay and schema")
    t.check("in-process replay identical", core1 == core2)
    modules = [kzperiod, kzperiod.exact, kzperiod.godel, kzperiod.words,
               kzperiod.arena, kzperiod.lanes, kzperiod.moves]
    patterns = [r"\bmath\b", r"\bfloat\b", r"\d\.\d", r"\brandom\b",
                r"\bFraction\b"]
    for mod in modules:
        with open(mod.__file__, encoding="utf-8") as fh:
            text = fh.read()
        for pat in patterns:
            t.check("%s clean of %s" % (mod.__name__, pat),
                    re.search(pat, text) is None)
    t.check("transcript carries no approximate values", _no_approx(core1))
    return t.gate()


def run_core():
    gates = [gate_g1(), gate_g2(), gate_g3(), gate_g4(), gate_g5()]
    return {"battery": "KT-PER4", "gates_home": 99, "charter": 101,
            "gates": gates,
            "total_checks": sum(g["checks"] for g in gates),
            "total_failures": sum(g["failures"] for g in gates),
            "total_refusals": sum(g["refusals"] for g in gates)}


def main():
    core1 = run_core()
    core2 = run_core()
    g6 = gate_g6(core1, core2)
    transcript = dict(core1)
    transcript["gates"] = core1["gates"] + [g6]
    transcript["total_checks"] = core1["total_checks"] + g6["checks"]
    transcript["total_failures"] = core1["total_failures"] + g6["failures"]
    transcript["total_refusals"] = core1["total_refusals"] + g6["refusals"]
    body = json.dumps(transcript, sort_keys=True, separators=(",", ":"))
    sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    print(json.dumps({"transcript": transcript, "results_sha256": sha},
                     sort_keys=True, separators=(",", ":")))
    return 1 if transcript["total_failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
