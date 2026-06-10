"""Chunked exact runner for the audited entry_state kernel with repriced
J-bits / literal overhead. State pickles between calls; recurrence exact."""
import sys, json, time, pickle, pathlib
import costs

J_BITS = int(sys.argv[1]); DEPTH = int(sys.argv[2]); OVERHEAD = int(sys.argv[3])
TOTAL = int(sys.argv[4]); BUDGET = float(sys.argv[5]) if len(sys.argv) > 5 else 33.0
costs.LOTUS_SEED_INDEX_J_BITS = J_BITS

import hit_distribution, superposition_model, entry_state
for m in (costs, hit_distribution, superposition_model, entry_state):
    for nm in dir(m):
        f = getattr(m, nm)
        if hasattr(f, 'cache_clear'):
            f.cache_clear()

from refresh_model import by_name
from superposition_model import SuperpositionConfig
from entry_state import initial_raw_state, run_pass, LITERAL_ENTRY_OVERHEAD_BITS

tag = f"_aud_{J_BITS}_{DEPTH}_{OVERHEAD}.pkl"
p = pathlib.Path(tag)
if p.exists():
    state, summary = pickle.loads(p.read_bytes())
else:
    state = initial_raw_state(1_000_000, 8)
    summary = []

refresh = by_name('permutation_plus_neutral_swaps')
super_cfg = SuperpositionConfig(16, 4, True, True)
t0 = time.time()
while state.pass_index < TOTAL and time.time() - t0 < BUDGET:
    overhead = OVERHEAD if state.pass_index == 0 else LITERAL_ENTRY_OVERHEAD_BITS
    state, row = run_pass(state, 5, DEPTH, 'greedy_largest_gain', super_cfg, refresh, overhead)
    summary.append((row.pass_index, row.bits_after, row.net_delta_pct_current))
p.write_bytes(pickle.dumps((state, summary)))
raw = state.original_raw_bits
done = state.pass_index
out = {"j": J_BITS, "overhead": OVERHEAD, "passes_done": done}
if done >= 11:
    eff = [r[2] for r in summary[1:11]]
    out["min_pct"] = round(min(eff), 5); out["avg_pct"] = round(sum(eff)/len(eff), 5)
    out["p1"] = round(summary[0][1]/raw, 5)
pb = next((r[0] for r in summary if r[1] < raw), None)
out["payback_so_far"] = pb
for h in (11, 50, 100, 200, 500):
    if done >= h:
        out[f"raw_{h}"] = round(summary[h-1][1]/raw, 5)
print(json.dumps(out))
