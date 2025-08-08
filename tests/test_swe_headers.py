import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from telomere.swe_seed_codec import encode_seed, decode_seed


def test_roundtrip_values():
    arities = [1, 2, 3, 4, 5]
    for ar in arities:
        for val in [0, 1, 255]:
            encoded = encode_seed(val, ar)
            assert decode_seed(encoded) == val

    assert decode_seed(encode_seed(0, 0)) is None
