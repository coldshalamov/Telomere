def encode_swe_literal(x: int) -> str:
    if x < 0:
        raise ValueError("SWE undefined for negative x")
    level = 0
    total = 0
    while True:
        count = 1 << level
        if x < total + count:
            index = x - total
            return format(index, f'0{level}b')
        total += count
        level += 1


def decode_swe_literal(bits: str) -> int:
    n = len(bits)
    base = sum(1 << i for i in range(n))
    suffix = int(bits, 2) if bits else 0
    return base + suffix


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
    # special case for zero
    if value == 0:
        return f"{ab}:00:0:0"
    payload = value + 1
    H4 = encode_swe_literal(payload)
    len4 = len(H4)
    H3 = encode_swe_literal(len4)
    len3 = len(H3)
    H2 = encode_swe_literal(len3)
    len2 = len(H2)
    H1 = encode_swe_literal(len2)
    return f"{ab}:{H1}:{H2}:{H3}:{H4}"


def decode_seed(code: str) -> tuple[int, int]:
    parts = code.split(":")
    ab = parts[0]
    if ab == "00":
        ar = 1
    elif ab == "01":
        ar = 2
    elif ab == "100":
        ar = 3
    elif ab == "101":
        ar = 4
    elif ab == "110":
        ar = 5
    elif ab == "111":
        ar = "literal"
    else:
        raise ValueError("Invalid arity")
    if parts[1:] == ["00", "0", "0"]:
        return 0, ar
    _, H1, H2, H3, H4 = parts
    p1 = decode_swe_literal(H4)
    return p1 - 1, ar
