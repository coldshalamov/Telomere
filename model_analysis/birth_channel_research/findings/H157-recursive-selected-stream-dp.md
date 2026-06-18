# H157 - Recursive Selected-Stream DP

Date: 2026-06-18

## Question

Can the non-greedy/slack idea work when every intermediate layer remains an
actual seed-bearing record stream?

Runnable artifact:

```text
model_analysis/birth_channel_research/H157-recursive_selected_stream_dp.py
```

## Model

This extends H150. For `P` passes, the final stored stream must be a visible
seed-record stream whose recursive decoding yields the target:

```text
x <- c1 <- c2 <- ... <- cP
```

No filler records, cloud mass, hidden rank stream, or stop selector is credited.
The parser is recursive: when an upper record emits its witness bits, those
bits are fed into the parser for the next lower pass, so lower passes can
bundle across upper-record boundaries.

Two caps are explicit:

```text
mid_cap   = maximum visible size of any generated intermediate layer
final_cap = maximum visible size of the final stored stream
```

These caps bound the exact state space. They are not metadata; only the final
visible record bits are counted.

## Results

Default exact rows:

```text
N  K  D  P  mid final  coverage  mean final bits  mean gain
3  3  3  1   18    44  1.000000        12.750000  -9.750000
3  3  3  2   18    44  0.500000        35.250000 -32.250000
3  3  3  3   18    44  0.000000              inf       -inf

4  4  4  1   24    56  1.000000        13.437500  -9.437500
4  4  4  2   24    56  1.000000        39.187500 -35.187500
4  4  4  3   24    56  0.000000              inf       -inf

5  4  4  1   26    60  1.000000        17.468750 -12.468750
5  4  4  2   26    60  1.000000        50.156250 -45.156250
5  4  4  3   26    60  0.000000              inf       -inf
```

Loose-cap probes:

```text
N=3,K=3,D=3,mid=24,final=128:
  P1 coverage 1.000000, final 12.750000, gain -9.750000
  P2 coverage 1.000000, final 43.875000, gain -40.875000
  P3 coverage 0.000000

N=3,K=3,D=3,mid=40,final=256:
  P1 coverage 1.000000, final 12.750000, gain -9.750000
  P2 coverage 1.000000, final 43.875000, gain -40.875000
  P3 coverage 0.375000, final 117.000000, gain -114.000000
```

## Reading

This is a lawful non-greedy recursive language: every layer is parseable and
seed-bearing. It still does not cross in the tested exact domain.

Adding selected recursive depth increases support only by spending much longer
visible seed streams. With larger caps, a three-pass path appears for some
targets, but the final stream is far larger than the raw target.

## Verdict

The user's non-greedy objection is valid as a search principle, but the next
required breakthrough is not more discarded alternatives. It is a closed
seed-bearing sublanguage whose visible selected streams have an entropy rate
below raw. H157 did not find that sublanguage.

