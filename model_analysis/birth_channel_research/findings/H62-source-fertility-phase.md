# H62 - Source Fertility Phase

Date: 2026-06-17

## Question

If the uniform/content-blind branch is blocked by counting, what would the
biology-shaped constructive branch have to look like?

H62 models a public fertility class rather than a learned per-file pattern:

```text
F has uniform mass f
Q gives states in F per-state lift a over uniform
the complement gets normalizing lift b = (1 - f*a)/(1 - f)
the source visits F with probability c
```

The score is:

```text
score(x) = log2(Q(x) / U(x))
```

Uniform data has expected score `<= 0`. A source-shaped lane crosses only when:

```text
E_source[score] > target_bits
```

So this is a clean way to price the "missing biological piece": the source must
keep visiting public high-fertility states more often than uniform does.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H62-source_fertility_phase.py
```

## Atom-Level Near Misses

For the nearest public-code misses, the needed source enrichment can be small:

```text
H59 miss = 0.053411/384 = 0.000139 bits/atom
H58 miss = 0.229195/384 = 0.000597 bits/atom
H7 atom miss = 0.011929 bits/atom
```

Representative thresholds:

```text
F mass f=0.10, Q lift a=2:
  uniform excess = 0.052933 bits
  H59 c* = 0.1454, enrichment c*/f = 1.454x
  H58 c* = 0.1458, enrichment c*/f = 1.458x
  H7  c* = 0.1555, enrichment c*/f = 1.555x

F mass f=0.01, Q lift a=8:
  uniform excess = 0.074737 bits
  H7 c* = 0.0379, enrichment c*/f = 3.790x
```

This says a public source/fertility law could cross the tiny atom-level misses
without needing huge source bias. That is promising only under the explicit
non-uniform premise. Uniform controls remain negative by construction.

## Record-Level Witness Gaps

For selected-record witness gaps, the required concentration is much stronger:

```text
H12 witness miss = 0.746 bits/record
H7 witness miss  = 1.357 bits/record
```

Representative thresholds:

```text
f=0.10,a=8:
  H12 c* = 0.5640, enrichment = 5.640x
  H7  c* = 0.6822, enrichment = 6.822x

f=0.01,a=64:
  H12 c* = 0.2957, enrichment = 29.566x
  H7  c* = 0.3776, enrichment = 37.757x
```

This separates two targets:

- public `Q` / whole-cover methods need only tiny per-atom source alignment;
- local witness-gap methods need much stronger class concentration unless the
  witness language itself gets cheaper.

## Recursive Maintenance Condition

One pass is not enough. To maintain recursive compression, the source-shaped
law must be invariant or self-renewing:

```text
c_t >= c*
c_{t+1} = Pr[encoded layer in F | c_t] >= c*
```

This is the useful biological analogy. A developmental or neutral-network
mechanism would help only if it repeatedly steers encoded layers into public
high-fertility states. If it merely explains the first layer and then maps back
to uniform, the next pass loses the gain.

## Verdict

H62 is the strongest constructive-looking branch after the uniform converse:

```text
public fertility/source law
+ stateless public decode geometry
+ recursive invariant c_{t+1} >= c*
+ uniform negative controls
```

It is not arbitrary-data compression. It is a possible Telomere-like recursive
source language, and the missing piece to test is whether such a public
fertility law can be defined without turning into an ordinary file-specific
pattern model.
