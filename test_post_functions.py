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
trials = 1
seed = 20260615

samples = generate_samples(block_bits, max_arity, atoms, trials, seed)
modes = {m.name: m for m in make_modes()}

cover = run_one_cover(samples[0], block_bits, max_arity, frontier, modes['markov1_arith_width_lotus_payload'])
records = cover.records

print(f"records: {len(records)}")
print(f"markov1_lotus_post: {modes['markov1_arith_width_lotus_payload'].post_cost(records, max_arity, frontier):.2f}")
print(f"markov1_penalty_0.05 post: {modes['markov1_penalty_0.05'].post_cost(records, max_arity, frontier):.2f}")
print(f"expected penalty diff: {0.05 * len(records):.2f}")

# Inspect the functions
penalty_mode = modes['markov1_penalty_0.05']
print(f"post function: {penalty_mode.post_cost}")
print(f"post closure defaults: {penalty_mode.post_cost.__defaults__}")

# Compute markov1_base_post manually
from total_cover_lotus_crossover import make_markov_with_penalty_modes
penalty_modes = make_markov_with_penalty_modes()
penalty_mode2 = [m for m in penalty_modes if m.name == 'markov1_penalty_0.05'][0]
print(f"penalty mode2 post: {penalty_mode2.post_cost(records, max_arity, frontier):.2f}")

# Check if markov1_base_post is accessible
import inspect
source = inspect.getsource(penalty_mode.post_cost)
print("post source:")
print(source)
