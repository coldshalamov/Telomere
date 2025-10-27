from __future__ import annotations

__all__ = [
    "encode_swe_literal",
    "decode_swe_literal",
    "encode_seed",
    "decode_seed",
]

# ---------------------------------------------------------------------------
# SWE literal helpers
# ---------------------------------------------------------------------------

def _encode_int(x: int) -> str:
    """Encode non-negative integer *x* using the Telomere prefix-free counter.

    Length sequence: 2 codes of length 1, 4 of length 2, 8 of length 3, …
    """
    level, total = 1, 0
    while True:
        count = 1 << level          # 2**level codes of this length
        if x < total + count:
            return format(x - total, f"0{level}b")
        total += count
        level += 1


def encode_swe_literal(n: int) -> str:
    """Encode positive integer *n* (≥1) as a SWE literal bit-string."""
    if n < 1:
        raise ValueError("SWE literals are 1-based (n ≥ 1)")
    return _encode_int(n - 1)


def decode_swe_literal(bits: str) -> int:
    """Decode a SWE literal bit-string back to the original integer."""
    L = len(bits)
    base = (1 << L) - 2             # total codes of shorter length
    return base + int(bits, 2) + 1

# ---------------------------------------------------------------------------
# Seed header helpers
# ---------------------------------------------------------------------------

_ARITY_TO_HEADER = {
    1: "00",
    2: "01",
    3: "100",
    4: "101",
    5: "110",
    0: "111",                       # literal passthrough
}

_HEADER_TO_ARITY = {v: k for k, v in _ARITY_TO_HEADER.items()}


def encode_seed(value: int, arity: int = 1) -> str:
    """Encode *value* as a Telomere seed.

    Parameters
    ----------
    value : int
        The numeric seed value to encode (≥0).
    arity : int, optional
        Block arity (1-5) or 0 for literal passthrough. Default is 1.
    """
    header = _ARITY_TO_HEADER.get(arity)
    if header is None:
        raise ValueError(f"Unsupported arity: {arity}")

    # Literal blocks stop after header.
    if header == "111":
        return header

    payload = encode_swe_literal(value + 1)          # Field5
    length_hdr = encode_swe_literal(len(payload))    # Field4
    jumpstarter = format(len(length_hdr) - 1, "03b") # Field3

    return header + jumpstarter + length_hdr + payload


def decode_seed(bits: str) -> int | None:
    """Decode a Telomere seed bit-string.

    Returns the integer value, or ``None`` for literal blocks.
    """
    if not bits:
        raise ValueError("Empty bitstring")

    header = bits[:2] if bits[:2] in ("00", "01") else bits[:3]
    arity = _HEADER_TO_ARITY.get(header)
    if arity is None:
        raise ValueError(f"Invalid arity header: {header}")

    if arity == 0:                                   # literal block
        return None

    pos = len(header)
    jump_val = int(bits[pos : pos + 3], 2) + 1       # Field3
    pos += 3
    len_hdr_bits = bits[pos : pos + jump_val]        # Field4
    payload_len = decode_swe_literal(len_hdr_bits)
    pos += jump_val
    payload_bits = bits[pos : pos + payload_len]     # Field5
    if len(payload_bits) != payload_len:
        raise ValueError("Bitstring ends before payload completes")

    return decode_swe_literal(payload_bits) - 1
