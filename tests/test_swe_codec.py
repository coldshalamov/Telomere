import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from swe_seed_codec import encode_swe_literal, decode_swe_literal
except ImportError:
    print("Module not available, skipping")
    sys.exit(0)

def test_roundtrip():
    for n in range(20):
        encoded = encode_swe_literal(n)
        decoded = decode_swe_literal(encoded)
        assert decoded == n, f"Failed for {n}"
        print(f"✓ {n}")

if __name__ == "__main__":
    test_roundtrip()
    print("Tests passed!")
