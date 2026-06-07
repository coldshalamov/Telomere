"""proof_kernel.costs — exact canonical record costs. No families, no extrapolation.

Source of truth: docs/FORMAT_CANONICAL.md (arity alphabet §2, J3D1 §4).
Everything is integer-exact; nothing here is approximate.
"""

ARITY_BITS = {1: 2, 2: 2, 3: 3, 4: 3, 5: 3}   # 00,01,100,101,110
LITERAL_BITS = 3                                # '111', charged once at init
JUMPSTARTER_BITS = 3
# The 3-bit jumpstarter caps the payload-length field at 7 bits, so canonical
# J3D1 expresses payloads of at most 127 bits: the wire format itself bounds
# the addressable seed space at 2^127 seeds. Format fact, not a model choice.
MAX_PAYLOAD_BITS = 127        # largest p with bit_length(p) <= 7


def arity_cost(a: int) -> int:
    """Canonical Kraft-complete arity codeword width. Arity 1..5 only."""
    return ARITY_BITS[a]


def j3d1_cost(payload_bits: int) -> int:
    """J3D1 seed-index field: jumpstarter(3) + length field + payload."""
    p = max(1, payload_bits)
    w = max(1, p.bit_length())
    assert w <= 7, "payload-length field exceeds 3-bit jumpstarter range"
    return JUMPSTARTER_BITS + w + p


def record_cost(a: int, payload_bits: int) -> int:
    """C(a,p) = arity_cost(a) + J3D1_cost(p). Exact."""
    return arity_cost(a) + j3d1_cost(payload_bits)


def min_record_bits() -> int:
    """Smallest record: arity 1 (2b) + J3D1 seed 0 (5b) = 7 bits (header.rs test)."""
    return record_cost(1, 1)


def pstar(r: int, a: int) -> int:
    """Largest J3D1-representable payload width p with record_cost(a,p) <= r;
    -1 if none. Exact; bounded by MAX_PAYLOAD_BITS (wire-format cap)."""
    best = -1
    p = 1
    limit = min(max(0, r), MAX_PAYLOAD_BITS)
    while p <= limit:
        if record_cost(a, p) <= r:
            best = p
            p += 1
        else:
            break
    return best


if __name__ == "__main__":
    assert min_record_bits() == 7
    assert sum(2.0 ** -b for b in list(ARITY_BITS.values()) + [LITERAL_BITS]) == 1.0
    assert pstar(664, 5) == 127 and pstar(23, 1) == 14 and pstar(6, 1) == -1
    print("costs.py self-check OK: 7-bit min record, Kraft-complete, pstar capped at 127")
