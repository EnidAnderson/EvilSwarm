"""Iterated words at one bit per letter.

omega0 = 0, omega1 = 1: a weight-w word is exactly a w-bit integer.
The {2,3} room grammar: blocks "01" (part 2) and "001" (part 3); a room
key is an admissible w-bit pattern: first bit 0, last bit 1, no
consecutive 1s, maximal zero-runs of length 1 or 2.
"""

from itertools import combinations

from .exact import LibRefusal

W0 = 0
W1 = 1


class Word:
    """A weight-w word carried as a w-bit integer key."""

    __slots__ = ("w", "key")

    def __init__(self, w, key):
        if not isinstance(w, int) or not isinstance(key, int):
            raise LibRefusal("non-integer word fields")
        if isinstance(w, bool) or isinstance(key, bool):
            raise LibRefusal("booleans are not word fields")
        if w < 1:
            raise LibRefusal("weight below 1")
        if key < 0 or key >= (1 << w):
            raise LibRefusal("key does not fit the weight")
        self.w = w
        self.key = key

    def __eq__(self, other):
        return (isinstance(other, Word) and self.w == other.w
                and self.key == other.key)

    def __repr__(self):
        return "Word(w=%d, key=%d)" % (self.w, self.key)


def compose(parts):
    """Concatenate {2,3} blocks into a word."""
    key = 0
    weight = 0
    for p in parts:
        if isinstance(p, bool) or not isinstance(p, int):
            raise LibRefusal("non-integer block")
        if p == 2:
            key = (key << 2) | 1
            weight += 2
        elif p == 3:
            key = (key << 3) | 1
            weight += 3
        else:
            raise LibRefusal("block out of grammar")
    return Word(weight, key)


def parse_blocks(word):
    """The unique {2,3} composition of an admissible word; refuses else."""
    key = word.key
    bits = word.w
    if bits < 2:
        raise LibRefusal("weight below 2")
    parts = []
    while bits > 0:
        if not (key & 1):
            raise LibRefusal("last bit not 1")
        key >>= 1
        bits -= 1
        z = 0
        while bits > 0 and not (key & 1):
            key >>= 1
            bits -= 1
            z += 1
        if z < 1 or z > 2:
            raise LibRefusal("zero-run out of grammar")
        parts.append(z + 1)
    parts.reverse()
    return parts


def is_room(key, w):
    try:
        parse_blocks(Word(w, key))
    except LibRefusal:
        return False
    return True


def compositions(w):
    if isinstance(w, bool) or not isinstance(w, int) or w < 0:
        raise LibRefusal("bad weight")
    if w == 0:
        yield ()
        return
    if w >= 2:
        for c in compositions(w - 2):
            yield (2,) + c
    if w >= 3:
        for c in compositions(w - 3):
            yield (3,) + c


def room_keys(w):
    return [compose(c) for c in compositions(w)]


def census_rec(w):
    """The census recurrence: c(n) = c(n-2) + c(n-3), c(0)=1, c(1)=0."""
    if isinstance(w, bool) or not isinstance(w, int) or w < 0:
        raise LibRefusal("bad weight")
    if w == 0:
        return 1
    if w == 1:
        return 0
    if w == 2:
        return 1
    table = [0] * (w + 1)
    table[0] = 1
    table[1] = 0
    table[2] = 1
    for n in range(3, w + 1):
        table[n] = table[n - 2] + table[n - 3]
    return table[w]


def word_from_indices(indices):
    """MZV index form (s1..sk) to the iterated-word blocks 0^(s-1) 1."""
    if not indices:
        raise LibRefusal("empty index tuple")
    key = 0
    weight = 0
    for i, s in enumerate(indices):
        if isinstance(s, bool) or not isinstance(s, int) or s < 1:
            raise LibRefusal("index below 1")
        if i == 0 and s < 2:
            raise LibRefusal("first index below 2")
        key = (key << s) | 1
        weight += s
    return Word(weight, key)


def shuffle_words(u, v):
    """The shuffle product as a multiset of merged words (bitmask interleaving)."""
    total = u.w + v.w
    ubits = [(u.key >> (u.w - 1 - i)) & 1 for i in range(u.w)]
    vbits = [(v.key >> (v.w - 1 - i)) & 1 for i in range(v.w)]
    out = {}
    for pos in combinations(range(total), u.w):
        chosen = set(pos)
        seq = []
        ui = 0
        vi = 0
        for i in range(total):
            if i in chosen:
                seq.append(ubits[ui])
                ui += 1
            else:
                seq.append(vbits[vi])
                vi += 1
        key = 0
        for b in seq:
            key = (key << 1) | b
        out[key] = out.get(key, 0) + 1
    return sorted(out.items())


def stuffle2(a, b):
    """Depth-2 index stuffle: zeta(a) zeta(b) = zeta(a,b)+zeta(b,a)+zeta(a+b)."""
    if (isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, int)
            or not isinstance(b, int) or a < 2 or b < 2):
        raise LibRefusal("bad stuffle indices")
    return sorted([(a, b), (b, a), (a + b,)])
