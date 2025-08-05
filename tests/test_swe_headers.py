import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from swe import encode_seed, decode_seed


def test_roundtrip_values():
    arities = [1, 2, 3, 4, 5, "literal"]
    for ar in arities:
        for val in [0, 1, 255]:
            assert decode_seed(encode_seed(val, ar)) == (val, ar)
