# Avenue H24 - active-lane Total-Cover

Author: Codex continuation from H22/H23. Date: 2026-06-17.
Status: all-open phase-lane test.

## HYPOTHESIS

H22 showed that public sparse lanes do not rescue sparse finite-K bundles. The
stronger positional idea is to make each active lane **all-open**:

```text
public phase selects lane
every atom in active lane is rewritten as Total-Cover records
inactive lanes carry in public order
decoder parses active records until arities sum to known lane size
```

Then no intra-lane hit bitmap and no boundary count are needed. Position tells
the decoder what is ready.

## MECHANISM

Runnable ledger:

- `../H24-active_lane_total_cover.py`

For a lane count `L`, one pass rewrites `1/L` of the stream. A full cycle
rewrites all lanes once. Since every active atom is covered, the per-active-atom
economics are the same as ordinary Total-Cover. The only extra charge in this
idealized ledger is a pass-count header amortized over the file:

```text
pass_count_bits_per_atom = log2(P + 1) / N
```

## RESULT SHAPE

This lane is expected to solve geometry, not witness cost:

```text
full-pass gain per input atom = active_gain / L
full-cycle gain per input atom = active_gain
```

So if the paid Total-Cover witness mode is negative, lane scheduling remains
negative. If the witness mode is positive, lane scheduling preserves it while
making salts/status public.

Smoke run:

```text
python model_analysis\birth_channel_research\H24-active_lane_total_cover.py ^
  --atoms 128 --trials 2 --block-bits 8 --max-arity 128 --frontiers 512 ^
  --lanes 1 4 ^
  --modes paid_iid_counts_lotus_payload arith_arity_width_lotus_payload free_boundary_oracle
```

The optimistic arithmetic stream produced an apparent positive small-lane row:

```text
arith_arity_width_lotus_payload, lanes=4
net cycle gain = +0.455471 bits/input atom
```

This is **not** a claimable result. That mode is the earlier optimistic stream
that does not pay all finite symbol subset/count information.

The stricter paid-count mode is negative:

```text
paid_iid_counts_lotus_payload, lanes=1
net cycle gain = -3.218999 bits/input atom

paid_iid_counts_lotus_payload, lanes=4
net cycle gain = -4.737202 bits/input atom
```

The unpaid oracle also stays negative in this small smoke after pass-count
amortization:

```text
free_boundary_oracle, lanes=1 -> -0.082042 bits/input atom
free_boundary_oracle, lanes=4 -> -0.218761 bits/input atom
```

## DECODE STORY

Decoder knows:

- phase/lane schedule;
- active lane atom count;
- record arities;
- public lane interleaving.

It reads active records until the arity sum equals the lane size, expands them
using position/phase salt, and carries inactive lanes in public order. No
birth-pass tag, open/carry map, final-position note, or sparse hit bitmap is
needed inside this idealized lane.

## VERDICT

All-open phase lanes are a good stateless decode geometry. They are not a new
compression source. They reduce the problem back to the Total-Cover witness
margin:

```text
solve witness economics -> phase lanes can schedule it statelessly
miss witness economics  -> phase lanes preserve the miss
```

The next useful positional work is therefore not another boundary trick. It is
to combine phase lanes with either:

- a paid witness mode that crosses;
- H18/H19 developmental fertility that changes the source prior;
- H20 cover-equivalence arithmetic that harvests duplicate-cover entropy.

Tesla's independent audit gives the dominance intuition: plain Total-Cover can
simulate a public phase lane while also seeing more cross-lane windows. Under
the same public salt/profile and honest witness costs, an all-open active lane
should not beat optimal plain Total-Cover except by boundary bookkeeping or by
using hidden source/selection metadata.
