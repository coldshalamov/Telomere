# H80 - Public-Q Fertility Lane

Date: 2026-06-17

## Question

H77 tested only one exact public fertility class:

```text
F = top 10% by log2(Q/U)
```

Can a gentler public class give a better source-shaped target for recursive
fertility while uniform controls stay negative?

Runnable artifact:

```text
model_analysis/birth_channel_research/H80-public_q_fertility_lane.py
```

## Setup

The kernel enumerates the same exact H74 tiny domain:

```text
B=1, N=12, K=6, D=8, domain=4096
```

It computes normalized public `Q`, then scores each word:

```text
score(x) = log2(Q(x) / U(x))
```

For each public class size `f`, it reports:

- `Q(F)`, the class mass under the public `Q` source;
- `mu_F` and `mu_O`, score inside and outside the class;
- value lift over uniform;
- d-choice placement lane losses;
- shuffled-class controls with the same class size;
- target threshold `c*`;
- `p_FF` needed when outside/background rate is uniform `f`.

## Domain Result

```text
raw bits:              12.000000
E_U log2(Q/U):         -1.814795
uniform excess bits:   +1.814795
E_Q log2(Q/U):         +1.365022
Q-source saving bits:  +1.365022
```

So the source-shaped public `Q` row is real, and the uniform control remains
negative.

## Class Sweep

Important rows:

```text
f      Q(F)    mu_F    mu_O    lift   lane16  lane64  shuffled max
0.025  0.2484  3.204  -1.943   5.019  1.591   0.320     0.697
0.10   0.5323  2.194  -2.261   4.009  0.295   0.002     0.349
0.25   0.7787  1.279  -2.846   3.093  0.015   0.000     0.165
0.50   0.9398  0.289  -3.918   2.104  0.000  -0.000     0.110
```

The top 25% class is much gentler than H77's top 10% class. It has lower
per-class score, but much higher `Q(F)`.

Public threshold and bottom controls:

```text
class             f       Q(F)    mu_F    mu_O    lift   lane16
F_positive Q>U   0.255   0.7839   1.254  -2.866   3.068   0.013
top 25%          0.250   0.7787   1.279  -2.846   3.093   0.015
bottom 25%       0.250   0.0079  -5.479  -0.593  -3.665   0.015
```

`F_positive = {x: Q(x)>U(x)}` nearly matches the top-25% row without choosing
an arbitrary fraction. The bottom-score control has the same support size and
lane cost but the opposite value lift.

## Target Thresholds

Targets are scaled to the finite word as:

```text
target_word = bits_per_atom * N
```

For the scaled H7 row:

```text
f=0.10: c*=0.5396, Q(F)=0.5323, pFF need=0.9146
f=0.25: c*=0.7247, Q(F)=0.7787, pFF need=0.9050
f=0.50: c*=0.9654, Q(F)=0.9398, pFF need=0.9821
```

For `f=0.25`, the public `Q` source concentration crosses the scaled H7 target
in this exact toy domain:

```text
Q(F) - c* = +0.0540
```

## Controls

Uniform control:

```text
E_U log2(Q/U) = -1.814795
```

Shuffled class controls:

```text
f=0.25 shuffled max lift = 0.165
```

The high-`Q` class lift is not reproduced by a same-size random class or by the
same-size bottom-score class.

## Verdict

H80 identifies a sharper source-shaped target: a gentler high-`Q` class can
cross the finite-domain source threshold better than H77's top 10% class.

This still does not solve roughly-all uniform recursion. It says the next real
mechanism to test is:

```text
Can Telomere's own stateless output law approximate this public Q source
or preserve the f=0.25 high-Q class across passes without witness-choice
leakage?
```

That requires measuring actual `p_FF` and `p_OF` for a concrete rewrite rule,
not just naming the public class.
