def encode_swe_literal(x: int) -> str:
    if x < 0:
        raise ValueError("SWE undefined for negative x")
    level = 0
    total = 0
    while True:
        count = 1 << level
        if x < total + count:
            index = x - total
            return '0' * level + format(index, f'0{level}b')
        total += count
        level += 1

def decode_swe_literal(bits: str) -> int:
    n = 0
    while n < len(bits) and bits[n] == '0':
        n += 1
    base = sum(1 << i for i in range(n))
    suffix = bits[n:]
    return base + int(suffix, 2) if suffix else base

def encode_seed(value: int, arity: int = 1) -> str:
    if arity == 1:
        ab = "00"
    elif arity == 2:
        ab = "01"
    elif arity == 3:
        ab = "100"
    elif arity == 4:
        ab = "101"
    elif arity == 5:
        ab = "110"
    elif arity == "literal":
        ab = "111"
    else:
        raise ValueError("Arity must be 1–5 or 'literal'")

    # Special case for zero: ab + "00000" (5 zeros after arity prefix)
    if value == 0:
        return ab + "00000"

    p = value + 1
    H4 = encode_swe_literal(p)
    H3 = encode_swe_literal(len(H4))
    H2 = encode_swe_literal(len(H3))
    H1 = encode_swe_literal(len(H2))
    return ab + H1 + H2 + H3 + H4

def decode_seed(code: str) -> tuple[int, int]:
    if code.startswith("00"):
        arity, i = 1, 2
    elif code.startswith("01"):
        arity, i = 2, 2
    elif code.startswith("100"):
        arity, i = 3, 3
    elif code.startswith("101"):
        arity, i = 4, 3
    elif code.startswith("110"):
        arity, i = 5, 3
    elif code.startswith("111"):
        arity, i = "literal", 3
    else:
        raise ValueError("Invalid arity prefix")

    # Special case for zero: "00000" after arity bits
    if code[i:i+5] == "00000":
        return 0, arity

    def read_swe(bits: str, offset: int) -> tuple[int, int]:
        n = 0
        while offset + n < len(bits) and bits[offset + n] == '0':
            n += 1
        # The SWE field has n leading zeros, then n bits (could be zero).
        size = n + (1 if n == 0 else 0) + n
        return decode_swe_literal(bits[offset:offset+size]), offset + size

    len2, j = read_swe(code, i)
    len3, k = read_swe(code, j)
    len4, l = read_swe(code, k)
    payload, _ = read_swe(code, l)
    return payload - 1, arity
