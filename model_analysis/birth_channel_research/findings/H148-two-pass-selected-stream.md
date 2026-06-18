# H148 - Two-Pass Selected Stream

Date: 2026-06-18

## Question

H146 used collective next-pass saving as a future-fertility score. What happens
when the second pass must be an actual selected visible record stream?

Runnable artifact:

```text
model_analysis/birth_channel_research/H148-two_pass_selected_stream.py
```

## Model

The kernel uses the same exact paid V1/J3D1 toy family as H146:

```text
x --pass 1--> c1 --pass 2--> c2
```

Both arrows are actual selected record-string descriptions. The final stored
stream after two recursive passes is `c2`; the decoder only needs the fixed
pass count and the visible records.

The test asks whether a larger intermediate `c1` can be useful because it has
a short selected parent `c2`.

## Result

Default exact support check:

```text
N=4,K=4,D=7,slack=8:
  pass1 coverage = 0.937500
  two-pass coverage = 0.000000

N=4,K=4,D=7,slack=12:
  pass1 coverage = 1.000000
  two-pass coverage = 0.000000
```

Looser exploratory sweeps started to enter combinatorial enumeration and were
not promoted. The next version should use a transfer-matrix/DP rather than
wider brute enumeration.

## Reading

This is stricter than H146. H146 shows that visible intermediates can score as
more fertile under collective next-pass mass. H148 requires the next pass to
select a real visible record stream, and the small exact family loses support
before it can test net compression.

## Verdict

The non-greedy route remains live, but the next constructive target is a
bounded recurrent transfer operator, not a wider brute-force enumeration of
second-pass visible strings.
