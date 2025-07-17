# CLI Output Fuzz Tester

`cli_output_fuzz.py` exercises the Telomere command line utilities and verifies
that their output is stable. It builds the binaries, runs a collection of tests,
and prints a short summary of results.

Run it with Python:

```bash
python3 tests/cli_output_fuzz.py
```

Example output:

```
Test Summary:
FAIL zeros: non ASCII output detected
FAIL ones: non ASCII output detected
FAIL random: non ASCII output detected
FAIL text: non ASCII output detected
PASS hash_dump: 010203  3  000102  9
PASS hash_dump_missing: Error reading input file 'hash_table.bin': No such file or directory (os error 2). Check that the file exists and the path is correct.
PASS hash_dump_corrupt: corrupt hash table file
```

Any entry marked `FAIL` indicates a deviation from the expected format or a
mismatched round‑trip.
