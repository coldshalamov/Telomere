# H155 - Closed-Lane Non-Greedy Target

Date: 2026-06-18

## Question

If we combine the closest lawful pieces, does non-greedy selected-stream lift
look large enough to pay the public-lane forced-rewrite witness miss?

Runnable artifact:

```text
model_analysis/birth_channel_research/H155-closed_lane_nongreedy_target.py
```

## Model

H155 is a cross-domain target ledger, not a unified production codec. It
combines measured rows from:

```text
H105: public two-epoch lanes + class-local rank, no readiness tax
H152: visible non-greedy selected-stream lift in a different tiny H96 domain
H151: closure-by-valid-stream support tax
H120: width-channel equivalence stress bill
H153: cloud/rank mass is not credited
```

No open/carry/birth-pass entropy is charged. Public lanes are assumed to make
readiness visible. The cloud column is diagnostic only.

The ledger asks whether the measured lift is numerically large enough to be a
target for the public-lane gap:

```text
base_after_lift = H105_base_gap - H152_visible_lift
closure_after_lift = H105_base_gap + H151_closure_tax - H152_visible_lift
width_after_lift = H105_base_gap + H120_width_bill - H152_visible_lift
```

## Results

Best base-only row:

```text
H105 target:
  mode = custom_record
  K = 6
  D = 12
  base gap = 1.781751 bits/word
  missing = 0.468557 bits/record
  implied records/word = 3.802635

H152 transfer:
  N = 6
  K = 5
  D = 7
  slack = 18
  visible non-greedy lift = 1.890625 bits/H152-word
  selected gain = -35.593750 bits/word
  cloud gap = 7.868868 bits

base_after_lift = -0.108874 bits/target-word
```

That is the good news. The measured visible non-greedy lift is large enough, as
a target-transfer magnitude, to matter on the best H105 public-lane witness
miss. This is not an observed combined-codec crossing.

But the remaining bills dominate:

```text
intermediate length ~= 18.515625 bits
H151 closure stress at rounded intermediate length = 8.733213 bits
closure_after_lift = +8.624339 bits/word

H120 width stress bill = 5.341012 bits/record
width_after_lift = +20.201047 bits/word
```

The best stacked row in the table still misses by `22.798591 bits/word`.
The closure and width columns are stress ledgers: H152's exact `y -> c -> x`
selected row already pays its explicit final stream, while H151/H120 show what
a future closed public-lane mechanism must internalize, make public, or pay.

## Reading

H155 finds a live but narrow constructive signal:

```text
non-greedy visible lift is in the right numerical range to pay the base
public-lane witness miss
```

That does not solve recursion. The same transfer row is still very negative as
an explicit selected stream, and it does not remove closure or width
parseability. H153 says the cloud cannot be credited as free capacity, and H154
says fixed-cell closure buys parseability by starving seed address space.

## Verdict

The next useful target is not a bigger cloud and not another hidden selector.
It is:

```text
an exact selected-stream transfer that preserves H152-style visible lift while
internalizing or making unnecessary the width and closure bills by construction,
without paying for that construction by destroying seed address space.
```

H155 is therefore the clearest "near but not enough" ledger for the public-lane
branch so far.
