import sys, json
import costs

J_BITS = int(sys.argv[1]); DEPTH = int(sys.argv[2]); OVERHEAD = int(sys.argv[3])
PASSES = int(sys.argv[4]) if len(sys.argv) > 4 else 500
costs.LOTUS_SEED_INDEX_J_BITS = J_BITS

import hit_distribution, superposition_model, entry_state
for m in (costs, hit_distribution, superposition_model, entry_state):
    for nm in dir(m):
        f = getattr(m, nm)
        if hasattr(f, 'cache_clear'):
            f.cache_clear()

from refresh_model import by_name
from superposition_model import SuperpositionConfig
from entry_state import run_profile

final, rows = run_profile(1_000_000, 8, 5, DEPTH, PASSES, 'greedy_largest_gain',
                          SuperpositionConfig(16, 4, True, True),
                          by_name('permutation_plus_neutral_swaps'),
                          initial_literal_overhead_bits=OVERHEAD)
raw = final.original_raw_bits
eff = [r.net_delta_pct_current for r in rows[1:11]]
pb = next((r.pass_index for r in rows if r.bits_after < raw), None)
c = {h: rows[h-1].bits_after/raw for h in (11,50,100,200,500) if len(rows)>=h}
out = {"j_bits": J_BITS, "depth": DEPTH, "overhead": OVERHEAD,
       "min_pct": min(eff), "avg_pct": sum(eff)/len(eff),
       "p1": rows[0].bits_after/raw, "payback": pb,
       "curve": {str(k): round(v,6) for k,v in c.items()}}
print(json.dumps(out))
