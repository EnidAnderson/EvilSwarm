"""Exact rationals as canonical integer pairs. All arithmetic is exact."""


class LibRefusal(Exception):
    """The refusal fence: out-of-contract inputs are refused, never coerced."""


def _gcd_abs(a, b):
    a = a if a >= 0 else -a
    b = b if b >= 0 else -b
    while b:
        a, b = b, a % b
    return a


class Q:
    """A rational number as a canonical (num, den) pair; den > 0; gcd 1."""

    __slots__ = ("n", "d")

    def __init__(self, n, d=1):
        if isinstance(n, bool) or isinstance(d, bool):
            raise LibRefusal("booleans are not numbers")
        if not isinstance(n, int) or not isinstance(d, int):
            raise LibRefusal("non-integer operand")
        if d == 0:
            raise LibRefusal("zero denominator")
        if d < 0:
            n, d = -n, -d
        g = _gcd_abs(n, d)
        if g > 1:
            n //= g
            d //= g
        self.n = n
        self.d = d

    def __eq__(self, other):
        return isinstance(other, Q) and self.n == other.n and self.d == other.d

    def __repr__(self):
        return "Q(%d, %d)" % (self.n, self.d)

    def add(self, other):
        return Q(self.n * other.d + other.n * self.d, self.d * other.d)

    def sub(self, other):
        return Q(self.n * other.d - other.n * self.d, self.d * other.d)

    def mul(self, other):
        return Q(self.n * other.n, self.d * other.d)

    def neg(self):
        return Q(-self.n, self.d)

    def div(self, other):
        """Division is a seam operation: exact, and refuses a zero divisor."""
        if other.n == 0:
            raise LibRefusal("division by zero")
        return Q(self.n * other.d, self.d * other.n)

    def height(self):
        """The height-ledger entry (N, D): |numerator| and denominator."""
        return (self.n if self.n >= 0 else -self.n, self.d)
