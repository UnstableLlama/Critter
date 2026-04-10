"""
Mulberry32 - simple 32-bit PRNG.
Ported from Buddi's Mulberry32.swift to produce identical buddy rolls.
"""

_MASK32 = 0xFFFFFFFF
_MASK32_SIGNED_MIN = 1 << 31


def _to_i32(val: int) -> int:
    """Interpret low 32 bits as signed Int32 (two's complement)."""
    val &= _MASK32
    if val >= _MASK32_SIGNED_MIN:
        return val - (1 << 32)
    return val


def _to_u32(val: int) -> int:
    """Interpret as unsigned UInt32."""
    return val & _MASK32


def _imul(a: int, b: int) -> int:
    """Signed 32-bit wrapping multiply (matches Swift &*)."""
    return _to_i32(a * b)


class Mulberry32:
    """Deterministic PRNG matching the Swift implementation exactly."""

    def __init__(self, seed: int):
        self._seed = _to_u32(seed)

    def next(self) -> float:
        a = _to_i32(self._seed)
        a = _to_i32(a + _to_i32(0x6D2B79F5))

        t = _imul(a ^ _to_i32(_to_u32(a) >> 15), 1 | a)
        t = _to_i32(
            t + _imul(t ^ _to_i32(_to_u32(t) >> 7), 61 | t)
        ) ^ t

        self._seed = _to_u32(a)

        result = _to_u32(t ^ _to_i32(_to_u32(t) >> 14))
        return result / 4_294_967_296.0
