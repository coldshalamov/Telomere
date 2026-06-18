# H136 - Batch Footprint Mask DP

## Question

Does a non-contiguous final-board/egg-carton batch witness create new
source-free compression if the footprint itself is public or paid?

This is the stronger version of H133. Instead of treating a batch as an arity
convolution, H136 tracks the whole uncovered board mask.

## Model

State:

```text
M = uncovered atom mask
i = first uncovered atom
```

A symbol chooses a footprint `sigma` containing `i`, then removes it:

```text
Z(M) = sum_sigma W(M,sigma) * Z(M \ sigma)
```

The kernel is intentionally generous:

```text
normalized witness-rank mass = 1 per footprint
```

So the only thing being tested is whether footprint geometry itself creates
mass. Valid local syntax requires:

```text
sum_sigma W(M,sigma) <= 1
```

at every state.

## Result

Exact `Fraction` DP, `B=1,N=12`.

```text
interval_normalized K=6:
  log2 Z = 0.000000
  max local mass = 0.000000
  valid = true

all_masks_normalized K=4:
  log2 Z = 0.000000
  max local mass = 0.000000
  valid = true

all_masks_ceil K=4:
  log2 Z = -0.377551
  max local mass = 0.000000
  valid = true

gap_pair_normalized:
  log2 Z = 0.000000
  max local mass = 0.000000
  valid = true
```

Positive rows are unpaid footprint syntax:

```text
all_masks_free K=4:
  log2 Z = 21.656226
  max local mass log2 = 7.857981
  valid = false

gap_pair_free:
  log2 Z = 7.400879
  max local mass log2 = 1.000000
  valid = false
```

## Interpretation

Egg-carton/non-contiguous footprints are excellent decode geometry: they can
make order, placement, and batch shape public. But public geometry alone reaches
at most zero source-free margin. Any positive crossing in this family comes from
unpaid footprint choice, which is exactly the hidden selector the final-board
rules were meant to price.

This does not kill final boards as scaffolding. It means the compression source
still has to be a positive witness family or real recursive fertility law, not
the footprint syntax itself.

## Artifact

`model_analysis/birth_channel_research/H136-batch_footprint_mask_dp.py`
