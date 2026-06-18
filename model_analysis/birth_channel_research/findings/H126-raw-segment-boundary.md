# H126 - Raw Segment Boundary

## Question

Can the H124 raw/record type stream be made parseable by grouping markerless
raw atoms into one or a few contiguous raw regions, with boundaries paid once
per layer?

This directly tests the "ready records first / not-ready raw region" idea.

## Result

One or two segments are not enough, and paying the boundary list is far above
the available margin.

At `atoms=128`, `passes=4`, `public_lane_raw`, `exact_arity`:

```text
S=1, free boundary:
  +0.018555 bits/atom/pass

S=1, paid boundary:
  +0.100788 bits/atom/pass

S=2, free boundary:
  +0.014648 bits/atom/pass

S=2, paid boundary:
  +0.160161 bits/atom/pass
```

Half-size shape check at `atoms=64`:

```text
S=4, free boundary:
  -0.013672 bits/atom/pass, fail 0.500000

S=4, paid boundary:
  +0.238685 bits/atom/pass, fail 0.500000
```

## Interpretation

Multiple raw regions improve the free geometry, but exact boundary lists cost
far more than the H124 raw fallback saves. A useful parse geometry would need a
public deterministic rule much closer to the H124 adaptive type stream than
fixed clocks or a small paid segment list.

## Artifact

`model_analysis/birth_channel_research/H126-raw_segment_boundary.py`
