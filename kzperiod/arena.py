"""The working-layout arena: flat, size-classed, handle-addressed.

Handles are never recycled: a freed handle stays dead forever, so a stale
handle can only refuse, never alias a new object. The snapshot is the
canonical serialization of live content, sorted by content: allocation
order dies at the snapshot seam.
"""

from . import godel
from .exact import LibRefusal

WORD_LIMIT = 1 << 31
SIZE_CLASSES = (1, 2, 4, 8, 16)


def _valid_word(x):
    if isinstance(x, bool) or not isinstance(x, int):
        raise LibRefusal("non-integer word")
    if x < 0:
        raise LibRefusal("negative word")
    if x >= WORD_LIMIT:
        raise LibRefusal("word beyond the machine width")
    return True


def _valid_payload(p):
    if not isinstance(p, (bytes, bytearray)):
        raise LibRefusal("payload must be bytes")
    p = bytes(p)
    if len(p) > SIZE_CLASSES[-1]:
        raise LibRefusal("payload beyond the size class ladder")
    return p


class Arena:
    """A live set of records: species, iterated words, payload bytes."""

    def __init__(self):
        self._records = {}
        self._next = 1

    def alloc(self, species, words, payload=b""):
        if isinstance(species, bool) or not isinstance(species, int):
            raise LibRefusal("non-integer species")
        if species < 0:
            raise LibRefusal("negative species")
        if not isinstance(words, list) or not words:
            raise LibRefusal("empty word list")
        for w in words:
            _valid_word(w)
        payload = _valid_payload(payload)
        handle = self._next
        self._next += 1
        self._records[handle] = (species, list(words), payload, True)
        return handle

    def free(self, handle):
        rec = self._records.get(handle)
        if rec is None:
            raise LibRefusal("invalid handle")
        if not rec[3]:
            raise LibRefusal("double free")
        self._records[handle] = (rec[0], rec[1], rec[2], False)

    def read(self, handle):
        rec = self._records.get(handle)
        if rec is None or not rec[3]:
            raise LibRefusal("invalid handle")
        return (rec[0], list(rec[1]), rec[2])

    def live_count(self):
        return sum(1 for r in self._records.values() if r[3])

    def integrity(self):
        for handle, rec in self._records.items():
            if (isinstance(handle, bool) or not isinstance(handle, int)
                    or handle < 1 or handle >= self._next):
                return False
            species, words, payload, live = rec
            if (isinstance(species, bool) or not isinstance(species, int)
                    or species < 0):
                return False
            if not isinstance(words, list) or not words:
                return False
            for w in words:
                if isinstance(w, bool) or not isinstance(w, int):
                    return False
                if w < 0 or w >= WORD_LIMIT:
                    return False
            if not isinstance(payload, bytes) or len(payload) > SIZE_CLASSES[-1]:
                return False
            if not isinstance(live, bool):
                return False
        return True

    def snapshot(self):
        """Canonical live-content image; allocator order does not survive."""
        out = []
        for rec in self._records.values():
            if rec[3]:
                out.append(godel.serialize([rec[0], rec[1], rec[2]]))
        out.sort()
        return out
