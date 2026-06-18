# H151 - Closure Kraft Ledger

Date: 2026-06-18

## Question

H149/H150 show that recursive support fails because decoded intermediates do
not usually land back inside the public record-stream language. Can we force
intermediates to be valid record streams cheaply enough to preserve compression?

Runnable artifact:

```text
model_analysis/birth_channel_research/H151-closure_kraft_ledger.py
```

## Model

For a fixed public record grammar, a uniformly random `t`-bit intermediate is
valid for the next decode pass with probability:

```text
parse_density(t) = #valid_record_streams_of_length_t / 2^t
```

Forcing seed outputs into that valid-stream subset costs match supply:

```text
closure_tax(t) = -log2(parse_density(t))
```

This is not wire metadata, but it is real entropy: the seed search has been
thinned by exactly this amount.

## Results

H150's exact grammar:

```text
B1,K4,D7:
  record Kraft mass = 0.129180908
  missing mass to prefix-complete = 0.870819092

t=8:  density = 0.007812, tax = 7.000000 bits
t=12: density = 0.023438, tax = 5.415037 bits
t=20: density = 0.001892, tax = 9.045804 bits
```

Slightly deeper 1-bit grammar:

```text
B1,K5,D8:
  record Kraft mass = 0.164222717

t=12: density = 0.027344, tax = 5.192645 bits
t=20: density = 0.002609, tax = 8.582147 bits
```

High-arity custom closure probes:

```text
B1,K16,D4:
  record Kraft mass = 0.099609375
  t=9/11/12 tax = 5.000000 bits
  t=8/10/16 have zero valid streams

B1,K32,D3:
  record Kraft mass = 0.074218750
  t=10/12 tax = 5.000000 bits
  t=8/9/11/16 have zero valid streams
```

Larger block toy rows improve the long-length tax but still remain multi-bit:

```text
B4,K32,D16:
  record Kraft mass = 0.296875358
  t=24 tax = 5.752072 bits
  t=64 tax = 10.563883 bits

B4,K128,D16:
  record Kraft mass = 0.296875358
  t=24 tax = 5.912537 bits
  t=64 tax = 10.019899 bits
```

## Reading

Closure by support restriction is not free. It thins the match search by
roughly 5-10 bits in the tested regimes, far above the H144 non-greedy rescue
target of `0.008625-0.040116` bits/atom/candidate.

A prefix-complete or literal fallback can make parseability cheap, but then the
selected final stream pays raw/literal length. That buys support by bloat, the
same behavior H150 measured at slack 20.

## Verdict

The missing mechanism cannot be merely "require generated intermediates to be
valid record streams." It must either make closure intrinsic to the same
compact record family with far lower support tax, or supply a real source /
fertility law whose entropy bill is stated and paid.
