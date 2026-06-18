# H147 - Upward Detour Collapse

Date: 2026-06-18

## Question

If the shortest seed path unfolds through larger intermediate states and only
later shrinks, does that create extra stateless recursive compression capacity?

Runnable artifact:

```text
model_analysis/birth_channel_research/H147-upward_detour_collapse.py
```

## Model

For fixed stateless decode, the whole upward/downward route collapses to one
final description string. Intermediate bloat does not increase the number of
final addresses.

If a final seed is allowed to try `T` hidden branches or stop depths and keep
the one that matches the target, the branch choice is a hidden channel costing:

```text
log2(T) bits
```

unless a public invariant derives it.

## Results

For 32-bit targets, deterministic final strings of exact length `n-G` cover at
most:

```text
G=1:  0.500000
G=2:  0.250000
G=4:  0.062500
G=8:  0.003906
G=16: 1.526e-05
```

Allowing all final lengths `<= n-G` roughly doubles the support but does not
change the scaling:

```text
G=8:  <= length coverage bound = 0.007812
G=16: <= length coverage bound = 3.052e-05
```

If hidden branches are allowed, the branch bill comes back:

```text
90% coverage, exact final length:
  branch bits = G + 1.203254
  net = -1.203254 bits

99.9% coverage, exact final length:
  branch bits = G + 2.788217
  net = -2.788217 bits
```

With all final lengths `<= n-G`, the constant improves by one bit, but high
coverage is still negative:

```text
90% coverage net = -0.203254 bits
99.9% coverage net = -1.788217 bits
```

## Reading

Upward detours are legitimate search paths. They can help the encoder find a
short final description. But in a stateless deterministic decoder they do not
multiply decode capacity; the final visible seed is still the only address.

## Verdict

The promising version is not "try hidden paths until one works." The promising
version is: find a public fertility invariant that makes the good path
derivable, or a visible recurrent record language whose selected strings carry
future fertility without a separate stop/referee channel.
