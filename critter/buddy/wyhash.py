"""
Wyhash - fast non-cryptographic hash.
Ported from Buddi's Wyhash.swift to produce identical buddy identities.
"""


_SECRET = [
    0xA0761D6478BD642F,
    0xE7037ED1A0B428DB,
    0x8EBC6AF09C88C6E3,
    0x589965CC75374CC3,
]

_MASK64 = (1 << 64) - 1


def _read(data: bytes, offset: int, nbytes: int) -> int:
    if nbytes <= 0 or offset >= len(data):
        return 0
    result = 0
    for i in range(nbytes):
        idx = offset + i
        if idx >= len(data):
            break
        result |= data[idx] << (i * 8)
    return result


def _mum(a: int, b: int) -> tuple[int, int]:
    product = (a & _MASK64) * (b & _MASK64)
    lo = product & _MASK64
    hi = (product >> 64) & _MASK64
    return lo, hi


def _mix(a: int, b: int) -> int:
    lo, hi = _mum(a, b)
    return (lo ^ hi) & _MASK64


def hash_str(key: str, seed: int = 0) -> int:
    """Hash a string, returning a u64. Matches Swift Wyhash.hash(seed:key:)."""
    data = key.encode("utf-8")
    return _sum64(seed, data)


def _sum64(seed: int, data: bytes) -> int:
    length = len(data)
    state0 = (seed ^ _mix((seed ^ _SECRET[0]) & _MASK64, _SECRET[1])) & _MASK64

    if length <= 16:
        if length >= 4:
            end = length - 4
            quarter = (length >> 3) << 2
            a = ((_read(data, 0, 4) << 32) | _read(data, quarter, 4)) & _MASK64
            b = ((_read(data, end, 4) << 32) | _read(data, end - quarter, 4)) & _MASK64
        elif length > 0:
            a = ((data[0] << 16) | (data[length >> 1] << 8) | data[length - 1]) & _MASK64
            b = 0
        else:
            a = 0
            b = 0
    else:
        state = [state0, state0, state0]
        i = 0

        if length >= 48:
            while i + 48 < length:
                for j in range(3):
                    a_round = _read(data, i + 8 * (2 * j), 8)
                    b_round = _read(data, i + 8 * (2 * j + 1), 8)
                    state[j] = _mix(
                        (a_round ^ _SECRET[j + 1]) & _MASK64,
                        (b_round ^ state[j]) & _MASK64,
                    )
                i += 48
            state[0] = (state[0] ^ state[1] ^ state[2]) & _MASK64

        remaining = data[i:]
        k = 0
        while k + 16 < len(remaining):
            state[0] = _mix(
                (_read(remaining, k, 8) ^ _SECRET[1]) & _MASK64,
                (_read(remaining, k + 8, 8) ^ state[0]) & _MASK64,
            )
            k += 16

        a = _read(data, length - 16, 8)
        b = _read(data, length - 8, 8)
        state0 = state[0]

    a = (a ^ _SECRET[1]) & _MASK64
    b = (b ^ state0) & _MASK64
    a_m, b_m = _mum(a, b)
    return _mix((a_m ^ _SECRET[0] ^ length) & _MASK64, (b_m ^ _SECRET[1]) & _MASK64)
