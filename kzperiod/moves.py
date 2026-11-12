"""Moves and proofs as integers: records, canonical ids, replay verification.

A proof is an ordered array of move records; a record is a species tag
plus a tuple of integers. The replay verifier solves the recorded linear
system in lane arithmetic, lifts, reconstructs under the certificate
height ledgers, and confirms everything again in exact rational
arithmetic. The transposition table keys on the canonical hash and
resolves collisions by full comparison, never by trust.
"""

from .exact import Q, LibRefusal
from .godel import serialize, serial_number, hash128
from .lanes import inv_mod, crt_lift, wang_reconstruct, modulus_product

SPECIES_RELATION = 1
SPECIES_CERTIFICATE = 2
SPECIES_CLAIM = 3

UNIT_KEY = 1


class MoveRecord:
    """One move: a species tag and an integer payload."""

    __slots__ = ("kind", "data")

    def __init__(self, kind, data):
        if isinstance(kind, bool) or not isinstance(kind, int):
            raise LibRefusal("non-integer species")
        if kind not in (SPECIES_RELATION, SPECIES_CERTIFICATE, SPECIES_CLAIM):
            raise LibRefusal("species outside the census")
        if not isinstance(data, (tuple, list)) or not data:
            raise LibRefusal("empty move data")
        for v in data:
            if isinstance(v, bool) or not isinstance(v, int):
                raise LibRefusal("non-integer move datum")
        self.kind = kind
        self.data = tuple(data)

    def canonical_list(self):
        return [self.kind, list(self.data)]

    def canonical_id(self):
        return serial_number(self.canonical_list())

    def __eq__(self, other):
        return (isinstance(other, MoveRecord) and self.kind == other.kind
                and self.data == other.data)

    def __repr__(self):
        return "MoveRecord(kind=%d, data=%r)" % (self.kind, self.data)


class Proof:
    """An ordered array of move records with a canonical identity."""

    __slots__ = ("records",)

    def __init__(self, records):
        if not isinstance(records, list) or not records:
            raise LibRefusal("empty proof")
        for r in records:
            if not isinstance(r, MoveRecord):
                raise LibRefusal("non-record in proof")
        self.records = list(records)

    def moves(self):
        return [r.canonical_list() for r in self.records]

    def proof_id(self):
        return serial_number(self.moves())


class TranspositionTable:
    """Hash-keyed with full-comparison collision resolution."""

    def __init__(self, hashfn=None):
        if hashfn is None:
            def hashfn(x):
                return hash128(x)
        self._hash = hashfn
        self._buckets = {}
        self.collisions = 0
        self.size = 0

    def _key(self, record):
        cl = record.canonical_list()
        return self._hash(cl), serialize(cl)

    def put(self, record, value):
        h, b = self._key(record)
        bucket = self._buckets.get(h)
        if bucket is None:
            self._buckets[h] = [(b, value)]
            self.size += 1
            return True
        for b2, _ in bucket:
            if b2 == b:
                return False
        self.collisions += 1
        bucket.append((b, value))
        self.size += 1
        return True

    def get(self, record):
        h, b = self._key(record)
        bucket = self._buckets.get(h)
        if bucket is None:
            return None
        for b2, v2 in bucket:
            if b2 == b:
                return v2
        return None


def weight4_proof():
    """The weight-4 two-clock identity as a five-record proof.

    Unknowns: v(5) = the word 0101, v(3) = the word 0011, v(1) = 1.
    Relation 1 (shuffle): 4*v(3) + 2*v(5) = 5/2.
    Relation 2 (stuffle): 2*v(5) + 1*v(1) = 5/2.
    Certificates and the claim pin v(5) = 3/4 and v(3) = 1/4.
    """
    return Proof([
        MoveRecord(SPECIES_RELATION, (4, 3, 4, 5, 2, 5, 2)),
        MoveRecord(SPECIES_RELATION, (4, 5, 2, 1, 1, 5, 2)),
        MoveRecord(SPECIES_CERTIFICATE, (4, 5, 3, 4)),
        MoveRecord(SPECIES_CERTIFICATE, (4, 3, 1, 4)),
        MoveRecord(SPECIES_CLAIM, (4, 5, 3, 4)),
    ])


def verify_weight4(proof, primes=(1019, 509, 1021)):
    """Replay-verify the weight-4 proof; return (X, Y, x, y, M)."""
    records = proof.records
    if len(records) != 5:
        raise LibRefusal("wrong record count for the weight-4 species")
    kinds = [r.kind for r in records]
    if kinds != [SPECIES_RELATION, SPECIES_RELATION, SPECIES_CERTIFICATE,
                 SPECIES_CERTIFICATE, SPECIES_CLAIM]:
        raise LibRefusal("wrong species sequence for the weight-4 species")
    rel1, rel2, cert1, cert2, claim = records
    if len(rel1.data) != 7 or len(rel2.data) != 7:
        raise LibRefusal("relation record of the wrong shape")
    if len(cert1.data) != 4 or len(cert2.data) != 4 or len(claim.data) != 4:
        raise LibRefusal("certificate or claim of the wrong shape")
    if any(d[0] != 4 for d in (rel1.data, rel2.data, cert1.data,
                               cert2.data, claim.data)):
        raise LibRefusal("weight tag mismatch")
    if rel1.data[1] != 3 or rel1.data[3] != 5:
        raise LibRefusal("relation 1 keys off the census")
    if rel2.data[1] != 5 or rel2.data[3] != UNIT_KEY:
        raise LibRefusal("relation 2 keys off the census")
    if cert1.data[1] != 5 or cert2.data[1] != 3 or claim.data[1] != 5:
        raise LibRefusal("certificate or claim key off the census")
    _, _, ca1, _, cb1, rn1, rd1 = rel1.data
    _, _, ca2, _, cb2, rn2, rd2 = rel2.data
    if min(ca1, cb1, ca2, cb2) < 1 or min(rd1, rd2) < 1:
        raise LibRefusal("non-positive coefficient or denominator")
    if min(cert1.data[2], cert1.data[3], cert2.data[2],
           cert2.data[3], claim.data[2], claim.data[3]) < 1:
        raise LibRefusal("certificate or claim below 1")

    # The linear system over the unknowns (X = v(5), Y = v(3)).
    a11, a12 = cb1, ca1
    a21 = ca2
    b1 = Q(rn1, rd1)
    b2 = Q(rn2, rd2).sub(Q(cb2, 1))

    m = modulus_product(primes)
    xlanes = []
    ylanes = []
    for p in primes:
        ap = (a11 % p, a12 % p, a21 % p)
        b1p = b1.n * inv_mod(b1.d, p) % p
        b2p = b2.n * inv_mod(b2.d, p) % p
        det = (ap[0] * 0 - ap[1] * ap[2]) % p
        if det == 0:
            raise LibRefusal("singular lane system")
        inv_det = inv_mod(det, p)
        xp = ((0 - ap[1] * b2p) * inv_det) % p
        yp = ((ap[0] * b2p - b1p * ap[2]) * inv_det) % p
        xlanes.append(xp)
        ylanes.append(yp)
    x = crt_lift(xlanes, primes)
    y = crt_lift(ylanes, primes)

    # Height ledgers at the seam: the certificates carry their own boxes.
    rx, sx = wang_reconstruct(x, m, cert1.data[2], cert1.data[3])
    xq = Q(rx, sx)
    if xq != Q(cert1.data[2], cert1.data[3]):
        raise LibRefusal("certificate 1 contradicts the reconstruction")
    ry, sy = wang_reconstruct(y, m, cert2.data[2], cert2.data[3])
    yq = Q(ry, sy)
    if yq != Q(cert2.data[2], cert2.data[3]):
        raise LibRefusal("certificate 2 contradicts the reconstruction")

    # Exact replay in the rational plane.
    lhs1 = Q(ca1, 1).mul(yq).add(Q(cb1, 1).mul(xq))
    if lhs1 != Q(rn1, rd1):
        raise LibRefusal("relation 1 fails exact replay")
    lhs2 = Q(ca2, 1).mul(xq).add(Q(cb2, 1))
    if lhs2 != Q(rn2, rd2):
        raise LibRefusal("relation 2 fails exact replay")
    if Q(claim.data[2], claim.data[3]) != xq:
        raise LibRefusal("claim contradicts the verified value")
    return (xq, yq, x, y, m)
