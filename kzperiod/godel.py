"""Canonical Goedel serialization: injective, deterministic, orderable.

Every finitary object receives a tagged, length-prefixed byte encoding;
the canonical serial number is the content address; the 128-bit hash is
a fast key whose collisions are resolved by full comparison upstream.
"""

import hashlib

from .exact import Q, LibRefusal
from .words import Word

TAG_INT = 1
TAG_Q = 2
TAG_LIST = 3
TAG_BYTES = 4
TAG_WORD = 5


def _varint(x):
    if x < 0:
        raise LibRefusal("negative varint")
    out = bytearray()
    while True:
        b = x & 0x7F
        x >>= 7
        if x:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _svarint(x):
    if x >= 0:
        return _varint(x * 2)
    return _varint(-x * 2 - 1)


def serialize(obj):
    if isinstance(obj, bool):
        raise LibRefusal("booleans are not canonical citizens")
    if isinstance(obj, int):
        return bytes([TAG_INT]) + _svarint(obj)
    if isinstance(obj, Q):
        return bytes([TAG_Q]) + _svarint(obj.n) + _svarint(obj.d)
    if isinstance(obj, list):
        return (bytes([TAG_LIST]) + _varint(len(obj))
                + b"".join(serialize(x) for x in obj))
    if isinstance(obj, bytes):
        return bytes([TAG_BYTES]) + _varint(len(obj)) + obj
    if isinstance(obj, Word):
        return bytes([TAG_WORD]) + _varint(obj.w) + _svarint(obj.key)
    raise LibRefusal("uncanonicalizable object")


def _read_varint(buf, pos):
    r = 0
    shift = 0
    while True:
        if pos >= len(buf):
            raise LibRefusal("truncated serialization")
        b = buf[pos]
        pos += 1
        r |= (b & 0x7F) << shift
        if not (b & 0x80):
            return r, pos
        shift += 7


def _read_svarint(buf, pos):
    z, pos = _read_varint(buf, pos)
    if z & 1:
        return -((z + 1) // 2), pos
    return z // 2, pos


def _des(buf, pos):
    if pos >= len(buf):
        raise LibRefusal("truncated serialization")
    tag = buf[pos]
    pos += 1
    if tag == TAG_INT:
        return _read_svarint(buf, pos)
    if tag == TAG_Q:
        n, pos = _read_svarint(buf, pos)
        d, pos = _read_svarint(buf, pos)
        return Q(n, d), pos
    if tag == TAG_LIST:
        n, pos = _read_varint(buf, pos)
        out = []
        for _ in range(n):
            v, pos = _des(buf, pos)
            out.append(v)
        return out, pos
    if tag == TAG_BYTES:
        n, pos = _read_varint(buf, pos)
        if pos + n > len(buf):
            raise LibRefusal("truncated bytes")
        return bytes(buf[pos:pos + n]), pos + n
    if tag == TAG_WORD:
        w, pos = _read_varint(buf, pos)
        key, pos = _read_svarint(buf, pos)
        return Word(w, key), pos
    raise LibRefusal("unknown tag")


def deserialize(buf):
    if not isinstance(buf, (bytes, bytearray)):
        raise LibRefusal("serialization must be bytes")
    b = bytes(buf)
    value, pos = _des(b, 0)
    if pos != len(b):
        raise LibRefusal("trailing bytes")
    return value


def serial_number(obj):
    """The orderable canonical serial number: the content address."""
    return int.from_bytes(b"\x01" + serialize(obj), "big")


def hash128(obj):
    """A 128-bit content hash; collisions resolved by full comparison."""
    return int.from_bytes(hashlib.sha256(serialize(obj)).digest()[:16], "big")
