"""The lane plane: exact rationals as per-prime residue stacks.

A rational matrix rides one dense integer matrix per prime; the height
ledger (N, D) with modulus product M > 2ND makes Wang reconstruction
unique at the seam. Accumulators are fenced to machine width: the
per-lane bound n*(p-1)^2 must stay below 2^63 so a device word never
overflows. Nothing here is approximate; every value is an integer.
"""

from .exact import Q, LibRefusal

ACC_LIMIT = 1 << 63


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def inv_mod(a, p):
    """Modular inverse; a non-invertible residue is refused, never coerced."""
    if isinstance(a, bool) or isinstance(p, bool) or not isinstance(a, int) \
            or not isinstance(p, int):
        raise LibRefusal("non-integer residue operands")
    if p <= 1:
        raise LibRefusal("modulus below the lane contract")
    a %= p
    try:
        return pow(a, -1, p)
    except ValueError:
        raise LibRefusal("non-invertible residue")


def modulus_product(primes):
    """Product of the lane moduli; pairwise coprimality is enforced."""
    if not isinstance(primes, tuple) or len(primes) < 1:
        raise LibRefusal("lane primes must be a non-empty tuple")
    for p in primes:
        if isinstance(p, bool) or not isinstance(p, int) or p <= 1:
            raise LibRefusal("bad lane modulus")
    for i in range(len(primes)):
        for j in range(i + 1, len(primes)):
            if primes[i] == primes[j] or _gcd(primes[i], primes[j]) != 1:
                raise LibRefusal("lane moduli not coprime")
    m = 1
    for p in primes:
        m *= p
    return m


class QMat:
    """A rational matrix as (integer numerator matrix) / (denominator)."""

    __slots__ = ("m", "n", "nums", "den")

    def __init__(self, m, n, nums, den):
        if isinstance(m, bool) or isinstance(n, bool) or isinstance(den, bool) \
                or not isinstance(m, int) or not isinstance(n, int) \
                or not isinstance(den, int):
            raise LibRefusal("non-integer matrix frame")
        if m < 1 or n < 1:
            raise LibRefusal("degenerate matrix shape")
        if den < 1:
            raise LibRefusal("denominator below 1")
        if not isinstance(nums, list) or len(nums) != m * n:
            raise LibRefusal("numerator block of the wrong size")
        for v in nums:
            if isinstance(v, bool) or not isinstance(v, int):
                raise LibRefusal("non-integer numerator entry")
        self.m = m
        self.n = n
        self.nums = list(nums)
        self.den = den

    @classmethod
    def from_qs(cls, rows):
        if not isinstance(rows, list) or not rows:
            raise LibRefusal("empty rational matrix")
        m = len(rows)
        if not all(isinstance(r, list) for r in rows):
            raise LibRefusal("rows must be lists")
        n = len(rows[0])
        if n < 1 or any(len(r) != n for r in rows):
            raise LibRefusal("ragged rational matrix")
        den = 1
        for row in rows:
            for q in row:
                if not isinstance(q, Q):
                    raise LibRefusal("non-rational entry")
                den = den * q.d // _gcd(den, q.d)
        nums = []
        for row in rows:
            for q in row:
                nums.append(q.n * (den // q.d))
        return cls(m, n, nums, den)

    def entry(self, i, j):
        return Q(self.nums[i * self.n + j], self.den)

    def height(self):
        """The height ledger (N, D) for the matrix as carried."""
        big = 0
        for v in self.nums:
            a = v if v >= 0 else -v
            if a > big:
                big = a
        return (big, self.den)

    def to_lanes(self, primes):
        """The residue stack: one dense integer matrix per lane."""
        modulus_product(primes)
        lanes = []
        for p in primes:
            if self.den % p == 0:
                raise LibRefusal("lane modulus divides the denominator")
            inv = inv_mod(self.den, p)
            lanes.append([v * inv % p for v in self.nums])
        return LaneStack(primes, lanes, self.m, self.n)


class LaneStack:
    """Per-prime dense residue matrices in a fixed lane order."""

    __slots__ = ("primes", "lanes", "m", "n")

    def __init__(self, primes, lanes, m, n):
        if not isinstance(primes, tuple) or not isinstance(lanes, list):
            raise LibRefusal("bad lane stack frame")
        if len(primes) != len(lanes) or len(primes) < 1:
            raise LibRefusal("lane count mismatch")
        for idx, lane in enumerate(lanes):
            if not isinstance(lane, list) or len(lane) != m * n:
                raise LibRefusal("lane of the wrong size")
            for v in lane:
                if isinstance(v, bool) or not isinstance(v, int):
                    raise LibRefusal("non-integer residue")
                if v < 0 or v >= primes[idx]:
                    raise LibRefusal("residue outside its lane modulus")
        self.primes = primes
        self.lanes = lanes
        self.m = m
        self.n = n

    def residue(self, lane_idx, i, j):
        return self.lanes[lane_idx][i * self.n + j]

    def entry_residues(self, i, j):
        return [lane[i * self.n + j] for lane in self.lanes]


def lane_matmul(a, b):
    """Fenced lane multiplication: exact integer accumulation per lane."""
    if a.primes != b.primes:
        raise LibRefusal("lane order mismatch")
    if a.n != b.m:
        raise LibRefusal("shape mismatch")
    out_lanes = []
    for idx in range(len(a.primes)):
        p = a.primes[idx]
        fence = a.n * (p - 1) * (p - 1)
        if fence >= ACC_LIMIT:
            raise LibRefusal("accumulator fence: lane bound beyond device word")
        la = a.lanes[idx]
        lb = b.lanes[idx]
        c = [0] * (a.m * b.n)
        for i in range(a.m):
            for j in range(b.n):
                acc = 0
                for k in range(a.n):
                    acc += la[i * a.n + k] * lb[k * b.n + j]
                c[i * b.n + j] = acc % p
        out_lanes.append(c)
    return LaneStack(a.primes, out_lanes, a.m, b.n)


def crt_lift(residues, primes):
    """Lift per-lane residues to the unique residue modulo the product."""
    if not isinstance(residues, list) or not isinstance(primes, tuple) \
            or len(residues) != len(primes) or len(primes) < 1:
        raise LibRefusal("bad lift frame")
    acc = residues[0] % primes[0]
    mod = primes[0]
    for r, p in zip(residues[1:], primes[1:]):
        if mod % p == 0:
            raise LibRefusal("non-coprime lift moduli")
        t = (r - acc) % p
        t = t * inv_mod(mod % p, p) % p
        acc = acc + mod * t
        mod = mod * p
    return acc


def wang_reconstruct(x, m, nbound, dbound):
    """Monagan-style rational reconstruction, inclusive box, strict M > 2ND.

    Returns the unique reduced (r, s) with r/s congruent to x modulo m,
    |r| <= nbound, s <= dbound; refuses when the uniqueness gate or the
    box is violated. The walk is the Euclid exchange on (m, x) carrying
    the coefficient lanes alongside.
    """
    if isinstance(x, bool) or isinstance(m, bool) or not isinstance(x, int) \
            or not isinstance(m, int) or isinstance(nbound, bool) \
            or isinstance(dbound, bool) or not isinstance(nbound, int) \
            or not isinstance(dbound, int):
        raise LibRefusal("non-integer reconstruction frame")
    if m <= 2 * nbound * dbound:
        raise LibRefusal("modulus product fails the uniqueness gate")
    if x < 0 or x >= m:
        raise LibRefusal("residue outside [0, modulus)")
    if x == 0:
        return (0, 1)
    w0, u0 = m, 0
    w1, u1 = x, 1
    while w0 > nbound:
        if w1 == 0:
            raise LibRefusal("walk exhausted with no boxed residue")
        q = w0 // w1
        w0, u0, w1, u1 = w1, u1, w0 - q * w1, u0 - q * u1
    r, s = w0, u0
    if s < 0:
        r, s = -r, -s
    if s == 0 or s > dbound:
        raise LibRefusal("reconstructed denominator outside the ledger")
    if _gcd(r if r >= 0 else -r, s) != 1:
        raise LibRefusal("reconstruction not in lowest terms")
    return (r, s)
