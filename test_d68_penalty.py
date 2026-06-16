#!/usr/bin/env python3
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from total_cover_lotus_crossover import (
    generate_samples, run_one_cover, make_modes, summarize_covers
)

block_bits = 24
max_arity = 8
frontier = 68
atoms = 256
trials = 48
seed = 20260615

samples = generate_samples(block_bits, max_arity, atoms, trials, seed)
modes = {m.name: m for m in make_modes()}

for name in ['markov1_arith_width_lotus_payload', 'markov1_penalty_0.05']:
    mode = modes[name]
    covers = [run_one_cover(trial, block_bits, max_arity, frontier, mode) for trial in samples]
    for c in covers[:1]:
        print(f"{name}: records={len(c.records)} charged={c.charged_bits:.2f}")
    row = summarize_covers(covers, block_bits, max_arity, frontier, mode.name)
    print(f"{name}: D={row.frontier} gain/atom={row.gain_per_atom:.4f} rec/atom={row.records_per_atom:.4f} total/rec={row.total_bits_per_record:.2f}")
