import json
from pathlib import Path

data = json.loads(Path('markov_penalty.json').read_text())
for r in data['results']:
    if r['mode'].startswith('markov1_penalty_0.05') and r['K'] == 8:
        n = r['nearest']
        print(f"mode={r['mode']} D={n['D']} gain={n['gain_per_atom']:.4f} rec/atom={n['records_per_atom']:.4f}")
