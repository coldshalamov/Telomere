# H127 - Type-Priced Refresh Sweep

## Question

Is there a sweet spot between sparse compressive replacement and total
replacement where raw-atom fallback maintains freshness and still compresses
after raw/record type placement is paid?

## Result

No tested rewrite quota crosses after type-stream accounting.

Focused sweep:

```text
public_lane_raw, exact_arity, q=0.10:
  min_rewrite 0.01..0.25
  raw lower-bound delta/pass: -0.012858 to -0.016764
  bitmap_net/pass:           +0.142941 to +0.147396
  run_net/pass:              +0.250441 to +0.260043

public_lane_raw, lane_exact_arity, q=0.10:
  min_rewrite 0.01..0.25
  raw lower-bound delta/pass: -0.019206 to -0.025391
  bitmap_net/pass:           +0.152125 to +0.167864
  run_net/pass:              +0.257665 to +0.274594
```

## Interpretation

The raw fallback branch has an apparent margin over a broad rewrite range, but
the raw/record type stream is consistently much larger than that margin. Lower
rewrite pressure does not reveal a paid crossing.

## Artifact

`model_analysis/birth_channel_research/H127-type_priced_refresh_sweep.py`
