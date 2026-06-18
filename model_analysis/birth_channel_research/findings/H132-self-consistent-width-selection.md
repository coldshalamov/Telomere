# H132 - Self-Consistent Width Selection

## Question

Can the partial-refresh sweet spot become paid and parseable if the cover
selector internalizes the width cost during selection?

Instead of selecting the locally shortest edges and then paying a separate
width stream, this kernel iterates:

```text
select covers using local cost + -log2 P(width | public context)
fit P(width | public context) from the selected covers
repeat
freeze the law
evaluate held-out trials
```

This tests the idea that allowing a little bloat and refreshing enough blocks
might make the chosen widths self-organize into a cheaper public distribution.

## Result

The width law did not collapse far enough.

Focused held-out row at `atoms=128`, `passes=4`, `min_rewrite=0.25`:

```text
public_lane_raw, lane_due_arity, public:
  delta/atom/pass = +0.041360
  width/record = 4.105557
  rewrite fraction = 0.340332
  due cover = 1.000000
  fail = 0.500000

public_lane_raw, target_arity, hidden diagnostic:
  delta/atom/pass = +0.026024
  width/record = 2.234600
  rewrite fraction = 0.359863
  due cover = 1.000000
  fail = 0.500000
```

Corrected-context mini check at `atoms=64`, `passes=3`,
`min_rewrite=0.25`:

```text
public_lane_raw, arity, public:
  delta/atom/pass = +0.024703
  width/record = 2.758183
  fail = 0.000000

public_lane_raw, target_arity, hidden diagnostic:
  delta/atom/pass = +0.017235
  width/record = 2.374375
  fail = 0.000000
```

## Interpretation

This directly tests the user's suggested branch: do not require every local
match to be individually compressive; allow small bloat so enough records are
refreshed, and choose the best paid cover from the whole lattice.

In this forced-refresh record-layer toy, the lattice exists and covers the due
cohort, but the paid selected-width distribution is still too expensive. Even
the hidden `target_arity` diagnostic remains positive, so the miss is not just
that the public arity/lane clock is too weak.

This does not close all partial-refresh ideas. It narrows the target:

- a new witness family must reduce selected-width entropy by more than this
  frozen-law objective did;
- or a public board/lane invariant must make interval composition visible
  without becoming a stored per-file selector;
- or recursive outputs must become non-uniform/fertile under a fixed public
  law, changing the source distribution rather than only the parser.

## Artifact

`model_analysis/birth_channel_research/H132-self_consistent_width_selection.py`
