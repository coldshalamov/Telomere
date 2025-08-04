#!/usr/bin/env python3
from swe import encode_seed, decode_seed
"""CLI Output Format Fuzz Tester for Telomere.

This script exercises the command line binaries shipped with Telomere and
verifies that their textual output remains stable.  It checks that outputs are
ASCII only, contain no trailing whitespace, and end with a single newline.  Both
normal operation and common error paths are covered.
"""

import os
import random
import subprocess
import tempfile
from pathlib import Path


# Build binaries first
subprocess.run(["cargo", "build", "--quiet", "--bins"], check=True)

TEL = Path("target/debug/telomere").resolve()
HASH_DUMP = Path("target/debug/hash_dump").resolve()


def ensure_ascii(line: str):
    try:
        line.encode("ascii")
    except UnicodeEncodeError:
        raise AssertionError("non ASCII output detected")


def ensure_clean(line: str):
    if not line.endswith("\n"):
        raise AssertionError("missing trailing newline")
    if line[:-1].endswith(" ") or "\t" in line:
        raise AssertionError("trailing whitespace detected")


def run(*args, cwd=None):
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd)


def roundtrip_test(data: bytes, label: str):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        inp = td / "input.bin"
        comp = td / "output.tlmr"
        outp = td / "out.bin"

        inp.write_bytes(data)
        res = run(TEL, "compress", str(inp), str(comp))
        assert res.returncode == 0, res.stderr
        ensure_ascii(res.stderr)
        ensure_clean(res.stderr)
        assert "Wrote compressed output" in res.stderr

        res = run(TEL, "decompress", str(comp), str(outp))
        assert res.returncode == 0, res.stderr
        ensure_ascii(res.stderr)
        ensure_clean(res.stderr)
        assert "Wrote decompressed output" in res.stderr

        assert outp.read_bytes() == data

        return label, res.stderr.strip()


def hash_dump_success(entries: bytes, args, label: str):
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        (td_path / "hash_table.bin").write_bytes(entries)
        res = run(HASH_DUMP, *map(str, args), cwd=td)
        assert res.returncode == 0, res.stdout
        ensure_ascii(res.stdout)
        ensure_clean(res.stdout)
        lines = res.stdout.splitlines()
        assert lines, "no output"
        assert lines[-1].startswith("Total matching seeds:"), "missing summary"
        for line in lines[:-1]:
            cols = line.split()
            assert len(cols) == 4, f"expected 4 columns, got {cols}"
        return label, lines[0] if len(lines) > 1 else lines[-1]


def hash_dump_error(entries: bytes | None, label: str):
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        if entries is not None:
            (td_path / "hash_table.bin").write_bytes(entries)
        res = run(HASH_DUMP, cwd=td)
        assert res.returncode != 0, "expected failure"
        ensure_ascii(res.stderr)
        ensure_clean(res.stderr)
        return label, res.stderr.strip()


def main():
    results = []

    def run_case(name, func, *args):
        try:
            sample = func(*args)
            results.append((name, True, sample[1]))
        except Exception as e:
            results.append((name, False, str(e)))

    # Compress/decompress tests
    run_case("zeros", roundtrip_test, bytes([0] * 32), "zeros")
    run_case("ones", roundtrip_test, bytes([0xFF] * 32), "ones")
    run_case("random", roundtrip_test, os.urandom(32), "random")
    run_case("text", roundtrip_test, b"The quick brown fox", "text")

    # Hash dump valid
    import struct
    entry1 = struct.pack("<3B B 4B", 1, 2, 3, 3, 0, 1, 2, 3)
    entry2 = struct.pack("<3B B 4B", 10, 11, 12, 1, 13, 0, 0, 0)
    entries = entry1 + entry2
    run_case("hash_dump", hash_dump_success, entries, ["1", "16"], "hash_dump")

    # Hash dump missing file and corrupt file
    run_case("hash_dump_missing", hash_dump_error, None, "hash_dump_missing")
    run_case("hash_dump_corrupt", hash_dump_error, b"bad", "hash_dump_corrupt")

    # Print summary table
    print("Test Summary:")
    for name, status, sample in results:
        flag = "PASS" if status else "FAIL"
        print(f"{flag} {name}: {sample}")


if __name__ == "__main__":
    main()
