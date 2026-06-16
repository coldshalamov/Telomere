#!/usr/bin/env python3
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from total_cover_lotus_crossover import (
    generate_samples, run_one_cover, make_modes, summarize_covers
)

block_bits = 24
max_arity = 8
atoms = 256
trials = 48
seed = 20260615

samples = generate_samples(block_bits, max_arity, atoms, trials, seed)
modes = {m.name: m for m in make_modes()}

for frontier in range(60, 80):
    covers = [run_one_cover(trial, block_bits, max_arity, frontier, modes['markov1_arith_width_lotus_payload']) for trial in samples]
    row = summarize_covers(covers, block_bits, max_arity, frontier, 'markov1')
    if row.gain_per_atom > -0.5:
        print(f"D={frontier} gain={row.gain_per_atom:.4f} rec/atom={row.records_per_atom:.4f} total/rec={row.total_bits_per_record:.2f}")
