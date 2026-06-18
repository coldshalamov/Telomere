# H145 - Unfold-Depth Stop Ledger

Date: 2026-06-18

## Question

Could a short seed unfold through larger intermediate states and only later
shrink to the target, so that "eventually" any seed can produce any file?

Runnable artifact:

```text
model_analysis/birth_channel_research/H145-unfold_depth_stop_ledger.py
```

## Model

If decode depth is fixed and public, each seed still names only one final
output. Extra time does not increase the number of outputs.

If the decoder may stop at any of `T` intermediate states, then `(seed, stop)`
has `T` times as many descriptions:

```text
coverage ~= 1 - exp(-T * 2^-G)
```

where `G` is seed saving in bits. But the stop time costs:

```text
log2(T) bits
```

unless a public invariant or finite checksum/referee pays for it.

## Results

To get 90% coverage:

```text
G=8  saved bits:  steps ~= 589.46,     stop bits = 9.203254
G=16 saved bits:  steps ~= 150902.22,  stop bits = 17.203254
G=32 saved bits:  steps ~= 9.89e9,     stop bits = 33.203254
```

If the stop time is stored, the net is negative by the coverage constant:

```text
90% coverage:  net if stop stored = -1.203254 bits
99.9% coverage: net if stop stored = -2.788217 bits
```

Fixed-depth example:

```text
G=16, fixed log2(T)=16:
  fixed-depth coverage = 1.526e-5
  stop-time coverage   = 0.632121
  net if stop stored   = 0
```

## Reading

Long unfolding is a valid compute-for-compression idea only if stop depth is
publicly fixed or cheaply derivable. Otherwise the stop choice is the metadata.
A checksum can referee a finite stop search, but its bits are the same budget
and ambiguity returns once `T` exceeds the referee capacity.

## Verdict

Upward unfolding does not by itself create a free recursive compression
channel. It becomes promising only if combined with a public invariant that
derives the stop depth, or with the H144 non-greedy future-value route where
the selected seed's later fertility is measured and paid by actual future
compression.
