# H98 - Partial Slack Refresh Kernel

Date: 2026-06-18

## Question

Can the user's partial-cover variant find a sweet spot between:

```text
only replace currently compressive/equal spans
```

and:

```text
rewrite every atom
```

by allowing `+1`, `+2`, or `+4` bit records so enough atoms become fresh targets
for later bundle passes?

Runnable artifact:

```text
model_analysis/birth_channel_research/H98-partial_slack_refresh_kernel.py
```

## Model

H98 keeps three ledgers separate:

```text
unpaid carry:
  raw carried atoms cost B bits and have no parse marker.
  This measures the optimistic refresh lattice only.

H2 charged:
  same selected covers, plus H2(rewritten_fraction) bits/input atom.
  This is a lower bound; it does not charge full cover-shape/arity placement.

literal rewrite:
  unmatched atoms are emitted as literal tokens with only a 3-bit marker.
  This is stateless and parseable, and is still more generous than exact
  byte-aligned V1 literal overhead.
```

An interval is searchable on a pass only if it contains at least one fresh atom.
If it is carried, its atoms become stale. If it is replaced by a record, the
visible record bits become fresh.

## Result

Default small sweep:

```text
configs:
  v1_B8_K5
  xarity_B4_K16
  xarity_B4_K32
slacks: 0,1,2,4
budgets bits/atom: 0.00,0.05,0.25
passes=5,trials=8
```

Best unpaid lattice row:

```text
v1_B8_K5, slack=0, budget=0.00
mean log2 rho = -0.000706
final fresh fraction = 0.000000
rewritten fraction ~= 0.010
```

Best unpaid row that keeps at least 10% fresh output:

```text
xarity_B4_K32, slack=4, budget=0.05
mean log2 rho = +0.014129
```

Best H2-charged lower-bound row:

```text
v1_B8_K5, slack=0, budget=0.00
mean log2 rho = +0.007534
```

Best stateless literal-rewrite lower-bound row:

```text
v1_B8_K5, slack=4
mean log2 rho = +0.346924
```

## Reading

The partial slack idea does create the intended tradeoff:

```text
replace very little -> may show tiny unpaid compression, but freshness dies
replace enough -> freshness survives, but the layer expands
```

Once even the binary ready/carry entropy lower bound is charged, every tested
row expands. The literal-rewrite stateless version expands by far more, even
with only a 3-bit literal marker.

## Verdict

The other agent's claimed gain could be real in the unpaid lattice sense, but
that is not yet a stateless recursive compression result.

This lane remains useful as a target generator: it tells us what replacement
fraction is needed to keep match opportunities alive. But a successful version
must either:

```text
1. make the selected/carry layout decoder-derived,
2. keep only a tiny near-total exception set, or
3. find enough record margin to pay H2/cover-shape/literal accounting.
```

H98 does not find that paid sweet spot.
